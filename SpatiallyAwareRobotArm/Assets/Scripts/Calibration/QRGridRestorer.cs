using UnityEngine;
using System.Collections.Generic;
using System.IO;
using Microsoft.MixedReality.OpenXR;
using TMPro;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace SA_XARM.Calibration
{
    public class QRGridRestorer : MonoBehaviour
    {
        // =========================
        // Inspector
        // =========================

        [Header("Dependencies")]
        [SerializeField] private ARMarkerManager markerManager;

        [Header("Markers")]
        [SerializeField] private string textMarkerA = "A"; // 原点
        [SerializeField] private string textMarkerB = "B"; // X軸方向

        [Header("JSON")]
        [SerializeField] private string jsonFileName = "qr_grid_config.json";
        [SerializeField] private bool autoRestoreWhenAnchorReady = true;

        [Header("Visual")]
        [SerializeField] private GameObject restorePrefab;     // 復元表示する点のPrefab
        [SerializeField] private Transform restoreParent;      // 親（任意）
        [SerializeField] private bool clearBeforeRestore = true;

        [Header("UI (optional)")]
        [SerializeField] private TextMeshProUGUI qrAStatusText;
        [SerializeField] private TextMeshProUGUI qrBStatusText;
        [SerializeField] private TextMeshProUGUI statusText;

        [Header("Debug")]
        [SerializeField] private bool doLog = true;

        // =========================
        // State
        // =========================

        private Vector3? posOrigin = null;
        private Vector3? posXEnd = null;

        private Matrix4x4 worldToAnchor; // World -> Anchor(Local)
        private bool isAnchorReady = false;

        private bool hasRestored = false;
        private readonly List<GameObject> spawned = new List<GameObject>();

        // =========================
        // Unity
        // =========================

        private void Start()
        {
            if (markerManager != null)
            {
                markerManager.markersChanged += OnMarkersChanged;
            }
            else
            {
                Log("markerManager is NULL", "yellow");
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
            // 手動復元（任意）
            if (Input.GetKeyDown(KeyCode.R))
            {
                TryRestore();
            }

            // 表示クリア（任意）
            if (Input.GetKeyDown(KeyCode.C))
            {
                ClearSpawned();
                hasRestored = false;
                UpdateUI();
            }
        }

        // =========================
        // Marker Handling
        // =========================

        private void OnMarkersChanged(ARMarkersChangedEventArgs args)
        {
            foreach (var m in args.added) ProcessMarker(m);
            foreach (var m in args.updated) ProcessMarker(m);

            // アンカーが作れて、オート復元ONなら復元
            if (autoRestoreWhenAnchorReady && isAnchorReady && !hasRestored)
            {
                TryRestore();
            }
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
                // 既存ロジックをそのまま使用
                worldToAnchor = GridCalculationLogic.CalculateAnchorMatrix(posOrigin.Value, posXEnd.Value);
                isAnchorReady = true;
            }

            UpdateUI();
        }

        // =========================
        // Restore
        // =========================

        public void TryRestore()
        {
            if (!isAnchorReady)
            {
                Log("Markers A & B not ready -> cannot restore.", "yellow");
                UpdateUI("Waiting for markers...");
                return;
            }

            string path = Path.Combine(Application.persistentDataPath, jsonFileName);
            if (!File.Exists(path))
            {
                Log($"JSON not found: {path}", "red");
                UpdateUI($"JSON not found:\n{path}");
                return;
            }

            try
            {
                if (clearBeforeRestore) ClearSpawned();

                string json = File.ReadAllText(path);

                var settings = new JsonSerializerSettings
                {
                    Formatting = Formatting.None,
                    MissingMemberHandling = MissingMemberHandling.Ignore,
                    NullValueHandling = NullValueHandling.Ignore,
                    Converters = new List<JsonConverter> { new Vector3Converter() }
                };

                var points = JsonConvert.DeserializeObject<List<GridPointData>>(json, settings);
                if (points == null || points.Count == 0)
                {
                    Log("JSON loaded but empty.", "yellow");
                    UpdateUI("JSON loaded but empty.");
                    return;
                }

                // Anchor(Local) -> World に戻す
                Matrix4x4 anchorToWorld = worldToAnchor.inverse;

                int restoredCount = 0;
                foreach (var p in points)
                {
                    Vector3 worldPos = anchorToWorld.MultiplyPoint3x4(p.localPos);

                    if (restorePrefab != null)
                    {
                        var go = Instantiate(
                            restorePrefab,
                            worldPos,
                            Quaternion.identity,
                            restoreParent != null ? restoreParent : null
                        );
                        go.name = $"RestoredPoint_{p.id}_({p.gridX},{p.gridY})";
                        spawned.Add(go);
                    }

                    restoredCount++;
                }

                hasRestored = true;
                Log($"✅ Restored {restoredCount} points from JSON.", "green");
                UpdateUI($"RESTORED: {restoredCount} points\n{path}");
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[RESTORE ERROR] {e}");
                Log($"❌ Restore Error: {e.Message}", "red");
                UpdateUI($"Restore Error:\n{e.Message}");
            }
        }

        private void ClearSpawned()
        {
            for (int i = 0; i < spawned.Count; i++)
            {
                if (spawned[i] != null) Destroy(spawned[i]);
            }
            spawned.Clear();
        }

        // =========================
        // UI
        // =========================

        private void UpdateUI(string overrideStatus = null)
        {
            if (qrAStatusText != null)
                qrAStatusText.text = posOrigin.HasValue ? "<color=green>OK</color>" : "<color=red>No</color>";

            if (qrBStatusText != null)
                qrBStatusText.text = posXEnd.HasValue ? "<color=green>OK</color>" : "<color=red>No</color>";

            if (statusText == null) return;

            if (!string.IsNullOrEmpty(overrideStatus))
            {
                statusText.text = overrideStatus;
                return;
            }

            if (!isAnchorReady)
            {
                statusText.text = "Waiting for Markers (A,B)...";
                return;
            }

            if (hasRestored)
            {
                statusText.text = "<color=green><b>RESTORED</b></color>\n(R: Restore / C: Clear)";
                return;
            }

            statusText.text = "Anchor Ready.\nPress <b>R</b> to Restore.";
        }

        // =========================
        // Logging
        // =========================

        private void Log(string msg, string color)
        {
            // SpatialDebugLog が無い環境でも落とさない
            var logger = SpatialDebugLog.Instance;
            if (logger != null)
            {
                logger.Log(msg, doLog, color);
            }
            else if (doLog)
            {
                Debug.Log($"[QRGridRestorer] {msg}");
            }
        }

        // =========================
        // Newtonsoft Vector3 Converter (safety)
        // =========================

        private class Vector3Converter : JsonConverter<Vector3>
        {
            public override void WriteJson(JsonWriter writer, Vector3 value, JsonSerializer serializer)
            {
                writer.WriteStartObject();
                writer.WritePropertyName("x"); writer.WriteValue(value.x);
                writer.WritePropertyName("y"); writer.WriteValue(value.y);
                writer.WritePropertyName("z"); writer.WriteValue(value.z);
                writer.WriteEndObject();
            }

            public override Vector3 ReadJson(JsonReader reader, System.Type objectType, Vector3 existingValue, bool hasExistingValue, JsonSerializer serializer)
            {
                JObject obj = JObject.Load(reader);

                float x = obj["x"] != null ? obj["x"].Value<float>() : 0f;
                float y = obj["y"] != null ? obj["y"].Value<float>() : 0f;
                float z = obj["z"] != null ? obj["z"].Value<float>() : 0f;

                return new Vector3(x, y, z);
            }
        }
    }
}
