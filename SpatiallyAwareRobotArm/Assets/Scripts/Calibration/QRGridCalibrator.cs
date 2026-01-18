using UnityEngine;
using Microsoft.MixedReality.OpenXR;
using TMPro;
using System.Collections.Generic;
using System.IO;
using SA_XARM.Network.Websocket;
using Newtonsoft.Json;

namespace SA_XARM.Calibration
{





    public class QRGridCalibrator : MonoBehaviour
    {
        // =========================
        // Inspector
        // =========================

        [Header("Dependencies")]
        [SerializeField] private ARMarkerManager markerManager;
        [SerializeField] private Transform probeTransform;

        [Header("Markers")]
        [SerializeField] private string textMarkerA = "A"; // 原点
        [SerializeField] private string textMarkerB = "B"; // X軸方向

        [Header("Grid Settings")]
        [Tooltip("横方向のグリッド数 (4x4なら4)")]
        [SerializeField] private int gridWidth = 4;

        [Tooltip("縦方向のグリッド数 (4x4なら4)")]
        [SerializeField] private int gridHeight = 4;

        [Header("UI")]
        [SerializeField] private TextMeshProUGUI qrAStatusText;
        [SerializeField] private TextMeshProUGUI qrBStatusText;

        [Tooltip("進行状況や完了メッセージ用")]
        [SerializeField] private TextMeshProUGUI statusText;

        [Header("Visual / Debug")]
        [SerializeField] private GameObject visualFeedbackPrefab;
        [SerializeField] private GameObject gridParent;
        [SerializeField] private bool doLog = true;

       

        private int TotalPoints => Mathf.Max(1, gridWidth) * Mathf.Max(1, gridHeight);

        private Vector3? posOrigin = null;
        private Vector3? posXEnd = null;
        private Matrix4x4 anchorMatrix;
        private bool isAnchorReady = false;

        private int currentRecordIndex = 0;
        private readonly List<GridPointData> recordedPoints = new List<GridPointData>();

        private bool hasSaved = false;

        // =========================
        // Unity
        // =========================

        private void Start()
        {
            Log("[QRGridCalibrator] Mode: Manual Teaching Grid", "white");

            if (markerManager != null)
            {
                markerManager.markersChanged += OnMarkersChanged;
            }
            else
            {
                Log("markerManager is NULL", "yellow");
            }

            // WebSocket (存在する場合だけ登録)
            if (WebSocketManager.Instance != null)
            {
                WebSocketManager.Instance.On<MouseKeyInput>("KeyInput", (input) =>
                {
                    if (input != null && input.key == "space")
                    {
                        Log("® Remote Space Key Received!", "green");
                        RecordCurrentPoint();
                    }
                });
            }
            else
            {
                Log("WebSocketManager.Instance is NULL (skip remote input)", "yellow");
            }

            UpdateUI();
        }

        private void OnDestroy()
        {
            if (markerManager != null)
                markerManager.markersChanged -= OnMarkersChanged;
        }

        private void Update()
        {
            if (Input.GetKeyDown(KeyCode.Space))
                RecordCurrentPoint();
        }

        // =========================
        // Marker Handling
        // =========================

        private void OnMarkersChanged(ARMarkersChangedEventArgs args)
        {
            // 記録が終わっていても、アンカー更新・UI更新はしていい
            foreach (var m in args.added) ProcessMarker(m);
            foreach (var m in args.updated) ProcessMarker(m);
        }

        private void ProcessMarker(ARMarker marker)
        {
            if (marker == null) return;

            string text = marker.GetDecodedString().Trim();

            if (text == textMarkerA)
            {
                posOrigin = marker.transform.position;
            }
            else if (text == textMarkerB)
            {
                posXEnd = marker.transform.position;
            }

            if (posOrigin.HasValue && posXEnd.HasValue)
            {
                anchorMatrix = GridCalculationLogic.CalculateAnchorMatrix(posOrigin.Value, posXEnd.Value);
                isAnchorReady = true;
            }

            UpdateUI();
        }

        // =========================
        // Recording
        // =========================

        public void RecordCurrentPoint()
        {
            if (probeTransform == null)
            {
                Log("probeTransform is NULL!", "yellow");
                return;
            }

            if (!isAnchorReady)
            {
                Log("Markers A & B not ready!", "yellow");
                return;
            }

            // すでに保存済み＝完全終了
            if (hasSaved)
            {
                Log("Already Completed (saved).", "yellow");
                return;
            }

            // 念のため：上限越えを防ぐ
            if (currentRecordIndex >= TotalPoints)
            {
                // ここに来た時点で保存漏れがありえるので救済
                Log("Reached end but not saved yet -> force save", "yellow");
                SaveJsonOnce();
                UpdateUI();
                return;
            }

            Vector3 worldPos = probeTransform.position;
            Vector3 localPos = anchorMatrix.MultiplyPoint3x4(worldPos);

            // 0始まり (x: 0..width-1, y: 0..height-1)
            int gx = currentRecordIndex % gridWidth;
            int gy = currentRecordIndex / gridWidth;

            recordedPoints.Add(new GridPointData
            {
                id = currentRecordIndex,
                gridX = gx,
                gridY = gy,
                localPos = localPos
            });

            Log($"Pt[{currentRecordIndex}] Grid({gx},{gy}) local:{localPos}", "white");

            if (visualFeedbackPrefab != null)
            {
                if (gridParent != null)
                    Instantiate(visualFeedbackPrefab, worldPos, Quaternion.identity, gridParent.transform);
                else
                    Instantiate(visualFeedbackPrefab, worldPos, Quaternion.identity);
            }

            currentRecordIndex++;

            // ★最後の1点を入れた瞬間に必ず保存
            if (currentRecordIndex == TotalPoints)
            {
                SaveJsonOnce();
            }

            UpdateUI();
        }

        // =========================
        // Save
        // =========================

            private void SaveJsonOnce()
            {
                if (hasSaved) return;

                try
                {
                    Log("💾 Starting Serialization...", "white");
                    
                    // Vector3のシリアライズエラーを防ぐための設定
                    var settings = new JsonSerializerSettings
                    {
                        ReferenceLoopHandling = ReferenceLoopHandling.Ignore,
                        Formatting = Formatting.Indented
                    };

                    string json = JsonConvert.SerializeObject(recordedPoints, settings);
                    
                    Log($"💾 Serialization Success. Length: {json.Length}", "white");

                    string path = Path.Combine(Application.persistentDataPath, "qr_grid_config.json");
                    
                    // ファイル書き込み
                    File.WriteAllText(path, json);
                    
                    hasSaved = true;
                    Log("✅ All points Saved!", "green");
                    Log($"Path: {path}", "gray");
                }
                catch (System.Exception e)
                {
                    // ここで Unity の標準ログにも出す
                    Debug.LogError($"[CRITICAL SAVE ERROR] {e}"); 
                    Log($"❌ Save Error: {e.Message}", "red");
                }
            }

        // =========================
        // UI
        // =========================

        private void UpdateUI()
        {
            if (qrAStatusText != null)
                qrAStatusText.text = posOrigin.HasValue ? "<color=green>OK</color>" : "<color=red>No</color>";

            if (qrBStatusText != null)
                qrBStatusText.text = posXEnd.HasValue ? "<color=green>OK</color>" : "<color=red>No</color>";

            if (statusText == null) return;

            int total = TotalPoints;

            if (hasSaved)
            {
                statusText.text = "<color=green><b>COMPLETE (SAVED)</b></color>";
                return;
            }  

            if (!isAnchorReady)
            {
                statusText.text = "Waiting for Markers...";
                return;
            }

            if (currentRecordIndex >= total)
            {
                // ここは基本来ない（SaveJsonOnce が走る）が、念のため
                statusText.text = "<color=yellow><b>COMPLETE (NOT SAVED?)</b></color>";
                return;
            }

            int nextX = currentRecordIndex % gridWidth;
            int nextY = currentRecordIndex / gridWidth;

            statusText.text =
                $"Point: <b>{currentRecordIndex}</b> / {total}\n" +
                $"Target: ({nextX}, {nextY})\n" +
                $"Press Space";
        }

        // =========================
        // Logging wrapper
        // =========================

        private void Log(string msg, string color)
        {
            // SpatialDebugLog が無い環境でも落とさない

                SpatialDebugLog.Instance.Log(msg, doLog, color);
         
        }
    }
}
