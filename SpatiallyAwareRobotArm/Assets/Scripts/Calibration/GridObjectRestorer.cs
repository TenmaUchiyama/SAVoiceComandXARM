using UnityEngine;
using Microsoft.MixedReality.OpenXR; 
using TMPro;
using System.Collections.Generic;
using System.IO;
using SA_XARM.Network.Websocket; 
using Newtonsoft.Json; 

namespace SA_XARM.Calibration
{
    public class GridObjectRestorer : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private ARMarkerManager markerManager;
        
        [Header("Settings")]
        [SerializeField] private string textMarkerA = "A"; // 原点
        [SerializeField] private string textMarkerB = "B"; // X軸方向
        [SerializeField] private GameObject objectToSpawnPrefab; // 復元するオブジェクト
        [SerializeField] private GameObject gridParent;

        [Header("UI")]
        // ▼ 変更箇所: 個別のステータス表示用
        [SerializeField] private TextMeshProUGUI qrAStatusText;
        [SerializeField] private TextMeshProUGUI qrBStatusText;

        [SerializeField] private TextMeshProUGUI statusText;

        [SerializeField] private bool doLog = true;

        // --- 内部データ ---
        private Vector3? posOrigin = null; // A
        private Vector3? posXEnd = null;   // B
        private List<GridPointData> loadedPoints = new List<GridPointData>();
        private bool restorationComplete = false;

        // Newtonsoft用クラス定義
        public class GridPointData
        {
            public int id;
            public Vector3 localPos; 
        }

        private void Start()
        {
            SpatialDebugLog.Instance.Log("[GridObjectRestorer] Initializing...", doLog);

            // 1. JSON読み込み
            if (!LoadJsonData()) return;

            // 2. マーカーイベント登録
            if (markerManager != null) markerManager.markersChanged += OnMarkersChanged;

          
                WebSocketManager.Instance.On<MouseKeyInput>("KeyInput", (input) =>
                {
                    if (input.key == "space")
                    {
                        SpatialDebugLog.Instance.Log("® Remote Space Key Received!", doLog, "green");
                        // メインスレッドで実行する必要があるため、Updateなどでフラグ監視するか、
                        // ここで即座に呼ぶならUnity API操作に注意（WebSocketライブラリの実装による）
                        // ※ここではメインスレッド前提で呼びます
                        TryRestoreObjects();
                    }
                });
         
            UpdateUI();
        }

        private void OnDestroy()
        {
            if (markerManager != null) markerManager.markersChanged -= OnMarkersChanged;
        }

        // --- JSON読み込み (Newtonsoft使用) ---
        private bool LoadJsonData()
        {
            string path = Path.Combine(Application.persistentDataPath, "qr_grid_config.json");
            
            if (!File.Exists(path))
            {
                SpatialDebugLog.Instance.LogError($"Config not found: {path}", doLog);
                if (statusText != null) statusText.text = "<color=red>Config File Not Found</color>";
                return false;
            }

            try
            {
                string json = File.ReadAllText(path);

                // ★ Newtonsoft.Json で List を直接デシリアライズ (ラッパー不要)
                loadedPoints = JsonConvert.DeserializeObject<List<GridPointData>>(json);
                
                if (loadedPoints != null && loadedPoints.Count > 0)
                {
                    SpatialDebugLog.Instance.LogSuccess($"Loaded {loadedPoints.Count} points.", doLog);
                    return true;
                }
                else
                {
                    SpatialDebugLog.Instance.LogError("JSON loaded but list is empty.", doLog);
                    return false;
                }
            }
            catch (System.Exception e)
            {
                SpatialDebugLog.Instance.LogError($"JSON Error: {e.Message}", doLog);
                return false;
            }
        }

        // --- マーカー認識 ---
        private void OnMarkersChanged(ARMarkersChangedEventArgs args)
        {
            if (restorationComplete) return;

            foreach (var m in args.added) ProcessMarker(m);
            foreach (var m in args.updated) ProcessMarker(m);
        }

        private void ProcessMarker(ARMarker marker)
        {
            string text = marker.GetDecodedString().Trim();

            if (text == textMarkerA) posOrigin = marker.transform.position;
            else if (text == textMarkerB) posXEnd = marker.transform.position;

            UpdateUI();
        }

        // --- 復元実行トリガー ---
        public void TryRestoreObjects()
        {
            if (restorationComplete) return;

            // マーカーが揃っていなければ実行しない
            if (!posOrigin.HasValue || !posXEnd.HasValue)
            {
                SpatialDebugLog.Instance.Log("Markers A & B not ready yet!", doLog, "yellow");
                return;
            }

            PerformRestoration();
        }

        private void Update()
        {
            if (Input.GetKeyDown(KeyCode.R)) TryRestoreObjects();
        }

        // --- 実際の復元処理 ---
        private void PerformRestoration()
        {
            SpatialDebugLog.Instance.Log("Restoring Objects...", doLog, "cyan");

            // 1. 基準行列（World -> Local）計算
            Matrix4x4 worldToLocalMatrix = GridCalculationLogic.CalculateAnchorMatrix(posOrigin.Value, posXEnd.Value);

            // 2. 逆行列（Local -> World）
            Matrix4x4 localToWorldMatrix = worldToLocalMatrix.inverse;

            // 3. オブジェクト生成
            foreach (var point in loadedPoints)
            {
                Vector3 targetWorldPos = localToWorldMatrix.MultiplyPoint3x4(point.localPos);

                if (objectToSpawnPrefab != null)
                {
                    GameObject obj = Instantiate(objectToSpawnPrefab, targetWorldPos, Quaternion.identity, gridParent.transform);
                    obj.name = $"Restored_Point_{point.id}";
                }
            }

            restorationComplete = true;
            SpatialDebugLog.Instance.LogSuccess("All Objects Restored!", doLog);
            UpdateUI();
        }

        // ▼ 変更箇所: UI更新ロジック (Calibratorと同じスタイルへ)
        private void UpdateUI()
        {
            // 1. Aのステータス
            if (qrAStatusText != null)
                qrAStatusText.text = posOrigin.HasValue ? "<color=green>OK</color>" : "<color=red>No</color>";

            // 2. Bのステータス
            if (qrBStatusText != null)
                qrBStatusText.text = posXEnd.HasValue ? "<color=green>OK</color>" : "<color=red>No</color>";

            // 3. 全体ステータス
            if (statusText != null)
            {
                if (restorationComplete)
                {
                    statusText.text = "<color=green><b>RESTORED</b></color>";
                }
                else if (loadedPoints.Count == 0)
                {
                    statusText.text = "No Data";
                }
                else if (posOrigin.HasValue && posXEnd.HasValue)
                {
                    statusText.text = "Ready to Restore\nPress <color=yellow>R Key</color>";
                }
                else
                {
                    statusText.text = "Waiting for Markers...";
                }
            }
        }
    }
}