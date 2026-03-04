
using UnityEngine;
using Microsoft.MixedReality.OpenXR;
using TMPro;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using SA_XARM.Network.Websocket;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace SA_XARM.Calibration
{
    [System.Serializable]
    public class GridPointData
    {
        public string id;
        public int gridX;
        public int gridY;
        public Vector3 localPos; // Anchor(Local)
    }

    [System.Serializable]
    public class RobotConfigData
    {
        public Vector3? robotLocalPos = null;      // Anchor(Local)
        public Vector3? robotLocalForward = null;  // Anchor(Local)
    }

    public class QRGridTool : MonoBehaviour
    {
        // =========================
        // Inspector
        // =========================
        [Header("Dependencies")]
        [SerializeField] private ARMarkerManager markerManager;
        [SerializeField] private Transform probeTransform;
        [SerializeField] private CommandClient commandClient;

        [Header("Markers")]
        [SerializeField] private string textMarkerA = "A";
        [SerializeField] private string textMarkerB = "B";
        [SerializeField] private string textMarkerRobot = "Robot";

        [Header("Grid Settings")]
        [SerializeField] private int gridWidth = 4;
        [SerializeField] private int gridHeight = 4;

        [Header("JSON (Local Files)")]
        [SerializeField] private string gridJsonFileName = "qr_grid_config.json";
        [SerializeField] private string robotJsonFileName = "qr_robot_config.json";

        [Header("WebSocket Event Names")]
        [SerializeField] private string wsSaveGridEvent = "SaveGridConfig";
        [SerializeField] private string wsSaveRobotEvent = "SaveRobotConfig";

        // Server events
        [SerializeField] private string wsRestoreGridEvent = "RestoreGridConfig";
        [SerializeField] private string wsRestoreRobotMarkerEvent = "RestoreRobotMarkerConfig";

        [Header("Behavior")]
        [SerializeField] private bool autoRestoreWhenAnchorReady = true;
        [SerializeField] private bool clearBeforeRestore = true;

        [Header("Table Height Policy")]
        [Tooltip("Restore時、worldPos.y を卓上(Origin=Aマーカー)の y に強制する")]
        [SerializeField] private bool forceWorldYToTableHeight = true;

        [Tooltip("Save時、localPos.y を 0 に固定してXZだけ保存する（forwardも水平化）")]
        [SerializeField] private bool saveXZOnly = true;

        // ===== Manual Marker (Inspector Test) =====
        [Header("Test / Manual Markers (No AR Build)")]
        [SerializeField] private bool useManualMarkers = false;
        [SerializeField] private Transform manualMarkerA;
        [SerializeField] private Transform manualMarkerB;
        [SerializeField] private Transform manualMarkerRobot;
        [SerializeField] private bool manualUpdateEveryFrame = true;
        [SerializeField] private bool disableARMarkerManagerWhenManual = true;

        [Header("Visual / Debug")]
        [SerializeField] private GameObject teachPointPrefab;   // grid teach visualization
        [SerializeField] private GameObject restorePointPrefab; // grid restore visualization
        [SerializeField] private Transform pointsParent;        // Grid points parent
        [SerializeField] private bool doLog = true;

        [Header("Robot Visual")]
        [SerializeField] private GameObject robotPointPrefab;
        [SerializeField] private Transform robotPointParent;    // Robot pose parent (separate from grid)

        [Header("UI")]
        [SerializeField] private TextMeshProUGUI qrAStatusText;
        [SerializeField] private TextMeshProUGUI qrBStatusText;
        [SerializeField] private TextMeshProUGUI statusText;

        // =========================
        // State
        // =========================
        private enum Mode { Select, Teach, Restore }
        private Mode mode = Mode.Select;

        private Vector3? posOrigin = null;
        private Vector3? posXEnd = null;

        private Matrix4x4 worldToAnchor; // World -> Anchor(Local)
        private bool isAnchorReady = false;

        private int currentRecordIndex = 0;
        private readonly List<GridPointData> recordedPoints = new List<GridPointData>();
        private bool hasSavedGrid = false;

        private bool hasRestored = false;
        private readonly List<GameObject> spawned = new List<GameObject>();

        private int TotalPoints => Mathf.Max(1, gridWidth) * Mathf.Max(1, gridHeight);

        // Robot (teach / restore)
        private Vector3? savedRobotLocalPos = null;        // local
        private Vector3? savedRobotLocalForward = null;    // local
        private bool hasSavedRobot = false;
        private GameObject spawnedRobotPoint = null;

        // ===== Remote restore buffering =====
        private List<GridPointData> pendingRemoteGridPoints = null;
        private Vector3? pendingRemoteRobotLocalPos = null;
        private Vector3? pendingRemoteRobotLocalForward = null;
        private readonly object lockObj = new object();

        private bool wsSubscribed = false;

        // Manual cache
        private Vector3 _lastManualA;
        private Vector3 _lastManualB;
        private Vector3 _lastManualRobot;
        private bool _hasManualCache = false;

        // =========================
        // Unity
        // =========================
        private void Start()
        {
            SpatialDebugLog.Instance.Log("[QRGridTool] Start -> Mode SELECT (Press Q=Teach / R=Restore)", doLog, "white");

            if (!useManualMarkers || !disableARMarkerManagerWhenManual)
            {
                if (markerManager != null)
                    markerManager.markersChanged += OnMarkersChanged;
                else
                    SpatialDebugLog.Instance.Log("markerManager is NULL", doLog, "yellow");
            }

            if (useManualMarkers)
                TryUpdateAnchorFromManual(force: true);

            EnsureWebSocketSubscriptions();
            UpdateUI();
        }

        private void OnDestroy()
        {
            if (markerManager != null)
                markerManager.markersChanged -= OnMarkersChanged;
        }

        private void Update()
        {
            if (!wsSubscribed)
                EnsureWebSocketSubscriptions();

            if (useManualMarkers && manualUpdateEveryFrame)
                TryUpdateAnchorFromManual(force: false);

            // ---- Execute remote restore on main thread ----
            List<GridPointData> gridToRestore = null;
            Vector3? robotLocalPosToRestore = null;
            Vector3? robotLocalForwardToRestore = null;

            lock (lockObj)
            {
                if (pendingRemoteGridPoints != null)
                {
                    gridToRestore = pendingRemoteGridPoints;
                    pendingRemoteGridPoints = null;
                }

                if (pendingRemoteRobotLocalPos.HasValue)
                {
                    robotLocalPosToRestore = pendingRemoteRobotLocalPos;
                    pendingRemoteRobotLocalPos = null;
                }

                if (pendingRemoteRobotLocalForward.HasValue)
                {
                    robotLocalForwardToRestore = pendingRemoteRobotLocalForward;
                    pendingRemoteRobotLocalForward = null;
                }
            }

            if (gridToRestore != null || robotLocalPosToRestore.HasValue)
            {
                SpatialDebugLog.Instance.Log("Executing Restore from Remote Data...", doLog, "green");
                SelectMode(Mode.Restore);

                if (clearBeforeRestore)
                    ClearSpawnedOnly();

                if (gridToRestore != null && gridToRestore.Count > 0)
                    RestoreFromPoints(gridToRestore);

                if (robotLocalPosToRestore.HasValue)
                {
                    Vector3 lf = robotLocalForwardToRestore ?? Vector3.forward; // fallback
                    RestoreRobotFromLocal(robotLocalPosToRestore.Value, lf);
                }
            }
        }

        // =========================
        // WebSocket Subscriptions
        // =========================
        private void EnsureWebSocketSubscriptions()
        {
            if (wsSubscribed) return;
            if (WebSocketManager.Instance == null) return;

            WebSocketManager.Instance.On<MouseKeyInput>("KeyInput", (input) =>
            {
                if (input == null) return;
                string k = (input.key ?? "").ToLowerInvariant();

                if (k == "q") SelectMode(Mode.Teach);
                else if (k == "r") SelectMode(Mode.Restore);
                else if (k == "space") OnSpacePressed();
                else if (k == "c") ClearAll();
                else if (k == "l") OnLPressedRecordRobot();
            });

            // RestoreGridConfig
            WebSocketManager.Instance.On(wsRestoreGridEvent, (jsonPayload) =>
            {
                SpatialDebugLog.Instance.Log($"[QRGridTool] {wsRestoreGridEvent} received", doLog);

                try
                {
                    var root = ParsePossiblyNestedPayload(jsonPayload);
                    JToken pointsToken = root?["gridPoints"];
                    var points = ParseGridPointsToken(pointsToken);

                    if (points != null && points.Count > 1)
                        points = points.OrderBy(p => p.id).ToList();

                    if (points != null && points.Count > 0)
                    {
                        lock (lockObj)
                        {
                            pendingRemoteGridPoints = points;
                        }
                        SpatialDebugLog.Instance.Log($"Queued remote GRID restore: {points.Count} pts", doLog, "cyan");
                    }
                    else
                    {
                        SpatialDebugLog.Instance.Log("Remote GRID restore: gridPoints is empty or missing.", doLog, "yellow");
                    }
                }
                catch (System.Exception e)
                {
                    Debug.LogError($"Remote GRID Parse Error: {e}");
                    SpatialDebugLog.Instance.Log($"GRID Parse Error: {e.Message}", doLog, "red");
                }
            });

            // RestoreRobotMarkerConfig (robotLocalPos + robotLocalForward)
            WebSocketManager.Instance.On(wsRestoreRobotMarkerEvent, (jsonPayload) =>
            {
                SpatialDebugLog.Instance.Log($"[QRGridTool] {wsRestoreRobotMarkerEvent} received", doLog);

                try
                {
                    var root = ParsePossiblyNestedPayload(jsonPayload);
                    JToken markerToken = root?["markerData"];

                    var pose = ParseRobotPose(markerToken); // (pos?, forward?)

                    if (pose.pos.HasValue)
                    {
                        lock (lockObj)
                        {
                            pendingRemoteRobotLocalPos = pose.pos.Value;
                            if (pose.forward.HasValue) pendingRemoteRobotLocalForward = pose.forward.Value;
                        }
                        SpatialDebugLog.Instance.Log("Queued remote ROBOT restore (pos/forward).", doLog, "cyan");
                    }
                    else
                    {
                        SpatialDebugLog.Instance.Log("Remote ROBOT restore: markerData missing robotLocalPos/localPos.", doLog, "yellow");
                    }
                }
                catch (System.Exception e)
                {
                    Debug.LogError($"Remote ROBOT Parse Error: {e}");
                    SpatialDebugLog.Instance.Log($"ROBOT Parse Error: {e.Message}", doLog, "red");
                }
            });

            wsSubscribed = true;
            SpatialDebugLog.Instance.Log("WebSocket subscriptions ready.", doLog, "gray");
        }

        // =========================
        // Mode / Input
        // =========================
        private void SelectMode(Mode next)
        {
            mode = next;

            if (mode == Mode.Teach)
            {
                SpatialDebugLog.Instance.Log("Mode => TEACH (Space: record grid, L: record robot)", doLog, "green");
                if (probeTransform != null) probeTransform.gameObject.SetActive(true);
            }
            else if (mode == Mode.Restore)
            {
                manualUpdateEveryFrame = false;
                SpatialDebugLog.Instance.Log("Mode => RESTORE (Space: Local Restore / J: Remote Restore)", doLog, "cyan");
                if (probeTransform != null) probeTransform.gameObject.SetActive(false);

                if (autoRestoreWhenAnchorReady && isAnchorReady && !hasRestored)
                    TryRestoreFromLocalFiles();
            }

            UpdateUI();
        }

        private void OnSpacePressed()
        {
            if (mode == Mode.Teach) RecordCurrentGridPoint();
            else if (mode == Mode.Restore) TryRestoreFromLocalFiles();
            else
            {
                SpatialDebugLog.Instance.Log("Mode SELECT: Press Q or R first.", doLog, "yellow");
                UpdateUI();
            }
        }

        private void OnLPressedRecordRobot()
        {
            if (mode != Mode.Teach)
            {
                SpatialDebugLog.Instance.Log("L is only for TEACH mode. Press Q first.", doLog, "yellow");
                return;
            }
            RecordRobotPoint();
        }

        // =========================
        // Marker Handling
        // =========================
        private void OnMarkersChanged(ARMarkersChangedEventArgs args)
        {
            if (useManualMarkers) return;

            foreach (var m in args.added) ProcessMarker(m);
            foreach (var m in args.updated) ProcessMarker(m);

            if (mode == Mode.Restore && autoRestoreWhenAnchorReady && isAnchorReady && !hasRestored)
                TryRestoreFromLocalFiles();
        }

        private void ProcessMarker(ARMarker marker)
        {
            if (marker == null) return;

            string text = marker.GetDecodedString().Trim();

            if (text == textMarkerA) posOrigin = marker.transform.position;
            else if (text == textMarkerB) posXEnd = marker.transform.position;
            else if (text == textMarkerRobot)
            {
                // NOTE: ARMarker gives us a Transform, but in your pipeline you decided to teach robot pose from probeTransform.
                // We keep marker only as optional debug / future use.
                _lastManualRobot = marker.transform.position;
            }

            RecomputeAnchorIfReady();
            UpdateUI();
        }

        private void TryUpdateAnchorFromManual(bool force)
        {
            if (manualMarkerA == null || manualMarkerB == null)
            {
                posOrigin = null;
                posXEnd = null;
                isAnchorReady = false;
                UpdateUI();
                return;
            }

            Vector3 a = manualMarkerA.position;
            Vector3 b = manualMarkerB.position;
            Vector3 r = (manualMarkerRobot != null) ? manualMarkerRobot.position : _lastManualRobot;

            if (!force)
            {
                if (_hasManualCache && a == _lastManualA && b == _lastManualB && r == _lastManualRobot)
                    return;
            }

            _hasManualCache = true;
            _lastManualA = a;
            _lastManualB = b;
            _lastManualRobot = r;

            posOrigin = a;
            posXEnd = b;

            RecomputeAnchorIfReady();

            if (mode == Mode.Restore && autoRestoreWhenAnchorReady && isAnchorReady && !hasRestored)
                TryRestoreFromLocalFiles();

            UpdateUI();
        }

        private void RecomputeAnchorIfReady()
        {
            if (posOrigin.HasValue && posXEnd.HasValue)
            {
                worldToAnchor = GridCalculationLogic.CalculateAnchorMatrix(posOrigin.Value, posXEnd.Value);
                isAnchorReady = true;
            }
            else
            {
                isAnchorReady = false;
            }
        }





        public void SetGridVisibility(bool isVisible)
        {


            SpatialDebugLog.Instance.Log($"SetGridVisibility: {isVisible}", doLog, "gray");
            foreach(var go in pointsParent.GetComponentsInChildren<Grid>())
            {
                go.SetGridVisibility(isVisible);
            }
        }   

        // =========================
        // Teach (Grid)
        // =========================
        public void RecordCurrentGridPoint()
        {
            if (probeTransform == null)
            {
                SpatialDebugLog.Instance.Log("probeTransform is NULL!", doLog, "yellow");
                return;
            }
            if (!isAnchorReady)
            {
                SpatialDebugLog.Instance.Log("Markers A & B not ready!", doLog, "yellow");
                return;
            }
            if (hasSavedGrid)
            {
                SpatialDebugLog.Instance.Log("Grid already saved. (Press C to reset)", doLog, "yellow");
                return;
            }

            if (currentRecordIndex >= TotalPoints)
            {
                SpatialDebugLog.Instance.Log("Reached end but not saved -> force save", doLog, "yellow");
                SaveGridJsonOnce();
                UpdateUI();
                return;
            }

            Vector3 worldPos = probeTransform.position;
            Vector3 localPos = worldToAnchor.MultiplyPoint3x4(worldPos);

            if (saveXZOnly)
            {
                localPos.y = 0f;
            }

            int gx = currentRecordIndex % gridWidth;
            int gy = currentRecordIndex / gridWidth;

            recordedPoints.Add(new GridPointData
            {
                id = currentRecordIndex.ToString(),
                gridX = gx,
                gridY = gy,
                localPos = localPos
            });

            if (teachPointPrefab != null)
            {
                var go = Instantiate(teachPointPrefab, worldPos, Quaternion.identity, pointsParent);
                go.name = $"TeachPoint_{currentRecordIndex}_({gx},{gy})";
                spawned.Add(go);
            }

            SpatialDebugLog.Instance.Log($"[TEACH] GridPt[{currentRecordIndex}] Grid({gx},{gy}) local: {localPos}", doLog, "white");

            currentRecordIndex++;

            if (currentRecordIndex == TotalPoints)
                SaveGridJsonOnce();

            UpdateUI();
        }

        private void SaveGridJsonOnce()
        {
            if (hasSavedGrid) return;

            try
            {
                string path = GetGridJsonPath();

                var settings = new JsonSerializerSettings
                {
                    Formatting = Formatting.Indented,
                    MissingMemberHandling = MissingMemberHandling.Ignore,
                    NullValueHandling = NullValueHandling.Ignore,
                    Converters = new List<JsonConverter> { new Vector3Converter() }
                };

                string json = JsonConvert.SerializeObject(recordedPoints, settings);

                if (WebSocketManager.Instance != null)
                    WebSocketManager.Instance.Send(wsSaveGridEvent, json);
                else
                    SpatialDebugLog.Instance.Log("WebSocketManager.Instance is NULL -> cannot send grid", doLog, "red");

                File.WriteAllText(path, json);

                hasSavedGrid = true;
                SpatialDebugLog.Instance.Log("✅ Saved GRID JSON locally and sent to Server", doLog, "green");
                SpatialDebugLog.Instance.Log($"[SAVE GRID] path = {path}", doLog, "gray");
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[SAVE GRID ERROR] {e}");
                SpatialDebugLog.Instance.Log($"❌ Save Grid Error: {e.Message}", doLog, "red");
            }
        }

        // =========================
        // Teach (Robot Pose) from probeTransform
        // =========================
        public void RecordRobotPoint()
        {
            if (!isAnchorReady)
            {
                SpatialDebugLog.Instance.Log("Markers A & B not ready -> cannot record robot.", doLog, "yellow");
                return;
            }

            if (probeTransform == null)
            {
                SpatialDebugLog.Instance.Log("probeTransform is NULL -> cannot record robot.", doLog, "red");
                return;
            }

            // World pose (INPUT)
            Vector3 worldPos = probeTransform.position;
            Vector3 worldForward = probeTransform.forward;

            // Convert to Anchor(Local)
            Vector3 localPos = worldToAnchor.MultiplyPoint3x4(worldPos);
            Vector3 localForward = worldToAnchor.MultiplyVector(worldForward);

            if (saveXZOnly)
            {
                localPos.y = 0f;
                localForward.y = 0f; // keep forward horizontal
            }
            localForward = localForward.sqrMagnitude > 1e-8f ? localForward.normalized : Vector3.forward;

            savedRobotLocalPos = localPos;
            savedRobotLocalForward = localForward;

            // Visualize (OUTPUT)
            if (robotPointPrefab != null)
            {
                if (spawnedRobotPoint != null)
                    Destroy(spawnedRobotPoint);

                Vector3 worldForwardViz = worldForward;
                if (saveXZOnly)
                {
                    worldForwardViz.y = 0f;
                    if (worldForwardViz.sqrMagnitude < 1e-8f) worldForwardViz = Vector3.forward;
                    worldForwardViz.Normalize();
                }

                spawnedRobotPoint = Instantiate(
                    robotPointPrefab,
                    worldPos,
                    Quaternion.LookRotation(worldForwardViz, Vector3.up),
                    robotPointParent  // Use separate parent (not grid's pointsParent)
                );

                spawnedRobotPoint.name = "TeachRobotPose";
                commandClient.SetRobotBaseTransform(spawnedRobotPoint.transform);
            }else{
                SpatialDebugLog.Instance.Log($"[TEACH] Robot local pos={localPos}, forward={localForward}", doLog, "white");

            }

            SpatialDebugLog.Instance.Log($"[TEACH] Robot local pos={localPos}, forward={localForward}", doLog, "white");

            SaveRobotJsonOverwrite();
            UpdateUI();
        }

        private void SaveRobotJsonOverwrite()
        {
            try
            {
                if (!savedRobotLocalPos.HasValue)
                {
                    SpatialDebugLog.Instance.Log("Robot local pos is null -> skip save.", doLog, "yellow");
                    return;
                }

                string path = GetRobotJsonPath();

                var data = new RobotConfigData
                {
                    robotLocalPos = savedRobotLocalPos,
                    robotLocalForward = savedRobotLocalForward
                };

                var settings = new JsonSerializerSettings
                {
                    Formatting = Formatting.Indented,
                    MissingMemberHandling = MissingMemberHandling.Ignore,
                    NullValueHandling = NullValueHandling.Ignore,
                    Converters = new List<JsonConverter> { new Vector3NullableConverter() }
                };

                string json = JsonConvert.SerializeObject(data, settings);

                if (WebSocketManager.Instance != null)
                    WebSocketManager.Instance.Send(wsSaveRobotEvent, json);
                else
                    SpatialDebugLog.Instance.Log("WebSocketManager.Instance is NULL -> cannot send robot", doLog, "red");

                File.WriteAllText(path, json);

                hasSavedRobot = true;
                SpatialDebugLog.Instance.Log("✅ Saved ROBOT JSON locally and sent to Server", doLog, "green");
                SpatialDebugLog.Instance.Log($"[SAVE ROBOT] path = {path}", doLog, "gray");
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[SAVE ROBOT ERROR] {e}");
                SpatialDebugLog.Instance.Log($"❌ Save Robot Error: {e.Message}", doLog, "red");
            }
        }

        // =========================
        // Restore (Grid)
        // =========================
        private void RestoreFromPoints(List<GridPointData> points)
        {
            if (!isAnchorReady)
            {
                SpatialDebugLog.Instance.Log("Markers A & B not ready -> cannot restore yet.", doLog, "yellow");
                return;
            }

            Matrix4x4 anchorToWorld = worldToAnchor.inverse;
            float tableY = posOrigin.HasValue ? posOrigin.Value.y : 0f;

            int restoredCount = 0;

            foreach (var p in points)
            {
                Vector3 local = p.localPos;
                if (saveXZOnly)
                    local.y = 0f;

                Vector3 worldPos = anchorToWorld.MultiplyPoint3x4(local);

                if (forceWorldYToTableHeight && posOrigin.HasValue)
                    worldPos.y = tableY;

                if (restorePointPrefab != null)
                {
                    var go = Instantiate(restorePointPrefab, worldPos, Quaternion.identity, pointsParent);
                    go.name = $"RestoredPoint_{p.id}_({p.gridX},{p.gridY})";

                    var gridComp = go.GetComponent<global::Grid>();
                    if (gridComp != null) gridComp.SetGridPosition(p.id.ToString(), p.gridX, p.gridY);

                    spawned.Add(go);
                }

                restoredCount++;
            }

            hasRestored = true;
            SpatialDebugLog.Instance.Log($"✅ Restored {restoredCount} grid points.", doLog, "green");
            UpdateUI();
        }

        // =========================
        // Restore (Robot Pose)
        // =========================
        private void RestoreRobotFromLocal(Vector3 robotLocalPos, Vector3 robotLocalForward)
        {
            if (!isAnchorReady)
            {
                SpatialDebugLog.Instance.Log("Markers A & B not ready -> cannot restore robot.", doLog, "yellow");
                return;
            }

            Matrix4x4 anchorToWorld = worldToAnchor.inverse;
            float tableY = posOrigin.HasValue ? posOrigin.Value.y : 0f;

            Vector3 localPos = robotLocalPos;
            Vector3 localForward = robotLocalForward;

            if (saveXZOnly)
            {
                localPos.y = 0f;
                localForward.y = 0f;
            }
            localForward = localForward.sqrMagnitude > 1e-8f ? localForward.normalized : Vector3.forward;

            Vector3 worldPos = anchorToWorld.MultiplyPoint3x4(localPos);
            Vector3 worldForward = anchorToWorld.MultiplyVector(localForward);
            if (saveXZOnly) worldForward.y = 0f;
            worldForward = worldForward.sqrMagnitude > 1e-8f ? worldForward.normalized : Vector3.forward;

            if (forceWorldYToTableHeight && posOrigin.HasValue)
                worldPos.y = tableY;

            if (robotPointPrefab != null)
            {
                if (spawnedRobotPoint != null) Destroy(spawnedRobotPoint);

                spawnedRobotPoint = Instantiate(
                    robotPointPrefab,
                    worldPos,
                    Quaternion.LookRotation(worldForward, Vector3.up),
                    robotPointParent  // Use separate parent (not grid's pointsParent)
                );

                spawnedRobotPoint.name = "RestoredRobotPose";
            }

            savedRobotLocalPos = robotLocalPos;
            savedRobotLocalForward = robotLocalForward;
            hasRestored = true;

            SpatialDebugLog.Instance.Log($"✅ Restored ROBOT pose. localPos={robotLocalPos}, localForward={robotLocalForward}", doLog, "green");
            UpdateUI();
        }

        // =========================
        // Restore (Local Files)
        // =========================
        public void TryRestoreFromLocalFiles()
        {
            if (!isAnchorReady)
            {
                SpatialDebugLog.Instance.Log("Markers A & B not ready -> cannot restore.", doLog, "yellow");
                UpdateUI();
                return;
            }

            bool restoredAny = false;

            var gridPoints = LoadGridFromFile();
            if (gridPoints != null && gridPoints.Count > 0)
            {
                if (clearBeforeRestore) ClearSpawnedOnly();
                RestoreFromPoints(gridPoints);
                restoredAny = true;
            }

            var robot = LoadRobotFromFile();
            if (robot.HasValue)
            {
                if (clearBeforeRestore && !restoredAny) ClearSpawnedOnly();

                Vector3 pos = robot.Value.pos;
                Vector3 fwd = robot.Value.forward ?? Vector3.forward; // fallback
                RestoreRobotFromLocal(pos, fwd);

                restoredAny = true;
            }

            if (!restoredAny)
                SpatialDebugLog.Instance.Log("Local restore: no grid file and no robot file found/valid.", doLog, "yellow");
        }

        private List<GridPointData> LoadGridFromFile()
        {
            string path = GetGridJsonPath();
            if (!File.Exists(path))
            {
                SpatialDebugLog.Instance.Log($"GRID JSON file not found: {path}", doLog, "red");
                return null;
            }

            try
            {
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
                    SpatialDebugLog.Instance.Log("GRID JSON loaded but empty.", doLog, "yellow");
                    return null;
                }
                return points;
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[RESTORE GRID ERROR] {e}");
                SpatialDebugLog.Instance.Log($"❌ Restore Grid Error: {e.Message}", doLog, "red");
                return null;
            }
        }

        private (Vector3 pos, Vector3? forward)? LoadRobotFromFile()
        {
            string path = GetRobotJsonPath();
            if (!File.Exists(path))
            {
                SpatialDebugLog.Instance.Log($"ROBOT JSON file not found: {path}", doLog, "red");
                return null;
            }

            try
            {
                string json = File.ReadAllText(path);

                var settings = new JsonSerializerSettings
                {
                    Formatting = Formatting.None,
                    MissingMemberHandling = MissingMemberHandling.Ignore,
                    NullValueHandling = NullValueHandling.Ignore,
                    Converters = new List<JsonConverter> { new Vector3NullableConverter() }
                };

                var data = JsonConvert.DeserializeObject<RobotConfigData>(json, settings);
                if (data == null || !data.robotLocalPos.HasValue)
                {
                    SpatialDebugLog.Instance.Log("ROBOT JSON loaded but robotLocalPos is missing.", doLog, "yellow");
                    return null;
                }

                Vector3 pos = data.robotLocalPos.Value;
                Vector3? fwd = data.robotLocalForward.HasValue ? data.robotLocalForward.Value : (Vector3?)null;
                return (pos, fwd);
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[RESTORE ROBOT ERROR] {e}");
                SpatialDebugLog.Instance.Log($"❌ Restore Robot Error: {e.Message}", doLog, "red");
                return null;
            }
        }

        // =========================
        // Clear / Reset
        // =========================
        private void ClearAll()
        {
            ClearSpawnedOnly();
            ResetTeachState();
            hasRestored = false;

            SpatialDebugLog.Instance.Log("Cleared spawned + reset teach state.", doLog, "yellow");
            UpdateUI();
        }

        private void ResetTeachState()
        {
            currentRecordIndex = 0;
            recordedPoints.Clear();
            hasSavedGrid = false;

            savedRobotLocalPos = null;
            savedRobotLocalForward = null;
            hasSavedRobot = false;

            if (spawnedRobotPoint != null)
            {
                Destroy(spawnedRobotPoint);
                spawnedRobotPoint = null;
            }
        }

        private void ClearSpawnedOnly()
        {
            for (int i = 0; i < spawned.Count; i++)
            {
                if (spawned[i] != null) Destroy(spawned[i]);
            }
            spawned.Clear();

            if (spawnedRobotPoint != null)
            {
                Destroy(spawnedRobotPoint);
                spawnedRobotPoint = null;
            }
        }

        private string GetGridJsonPath()
        {
            return Path.Combine(Application.persistentDataPath, gridJsonFileName);
        }

        private string GetRobotJsonPath()
        {
            return Path.Combine(Application.persistentDataPath, robotJsonFileName);
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

            string modeText = mode switch
            {
                Mode.Select => "<b>MODE:</b> SELECT (Q=Teach / R=Restore)",
                Mode.Teach => "<b>MODE:</b> TEACH (Space=Grid, L=Robot, C=Clear)",
                Mode.Restore => "<b>MODE:</b> RESTORE (Space=Local Restore / J=Remote Restore)",
                _ => "<b>MODE:</b> ?"
            };

            string anchorText = isAnchorReady
                ? "<color=green>Anchor: READY</color>"
                : "<color=yellow>Anchor: waiting A/B...</color>";

            string extra = "";

            if (useManualMarkers)
                extra += "<size=80%><color=cyan>ManualMarker: ON</color></size>\n";

            if (mode == Mode.Teach)
            {
                string gridStatus = hasSavedGrid ? "<color=green><b>GRID SAVED</b></color>" : "Space to record grid";
                string robotStatus = hasSavedRobot ? "<color=green><b>ROBOT SAVED</b></color>" : "L to record robot";
                extra += $"Grid: {currentRecordIndex}/{TotalPoints}  {gridStatus}\n"
                      + $"Robot: {(savedRobotLocalPos.HasValue ? "Ready" : "None")}  {robotStatus}";
            }
            else if (mode == Mode.Restore)
            {
                extra += hasRestored ? "<color=green><b>RESTORED</b></color>" : "Waiting remote (J) or Space local restore";
            }
            else
            {
                extra += "Press Q or R";
            }

            statusText.text =
                $"{modeText}\n{anchorText}\n{extra}\n"
                + $"<size=60%>GRID: {GetGridJsonPath()}\nROBOT: {GetRobotJsonPath()}</size>";
        }

        // =========================
        // Remote Parsing
        // =========================
        private JObject ParsePossiblyNestedPayload(string jsonPayload)
        {
            if (string.IsNullOrWhiteSpace(jsonPayload))
                return null;

            string normalized = jsonPayload.Trim();

            // "\"{...}\"" -> "{...}"
            if (normalized.Length >= 2 && normalized[0] == '"' && normalized[normalized.Length - 1] == '"')
            {
                try { normalized = JsonConvert.DeserializeObject<string>(normalized); }
                catch { /* keep */ }
            }

            JToken token = JToken.Parse(normalized);

            // packet case: {"eventId":"X","payload":"{...}"}
            if (token.Type == JTokenType.Object)
            {
                var obj = (JObject)token;
                if (obj["payload"] != null && obj["payload"].Type == JTokenType.String)
                {
                    string inner = obj["payload"].Value<string>();
                    if (!string.IsNullOrWhiteSpace(inner))
                    {
                        inner = inner.Trim();
                        if (inner.Length >= 2 && inner[0] == '"' && inner[inner.Length - 1] == '"')
                        {
                            try { inner = JsonConvert.DeserializeObject<string>(inner); } catch { }
                        }
                        token = JToken.Parse(inner);
                    }
                }
            }

            return token as JObject;
        }

        private List<GridPointData> ParseGridPointsToken(JToken token)
        {
            if (token == null) return null;

            if (token.Type == JTokenType.String)
            {
                var inner = token.Value<string>();
                if (!string.IsNullOrWhiteSpace(inner))
                    token = JToken.Parse(inner);
            }

            if (token.Type == JTokenType.Object)
            {
                var obj = (JObject)token;
                var arr = new JArray();
                foreach (var prop in obj.Properties())
                    arr.Add(prop.Value);
                token = arr;
            }

            if (token.Type != JTokenType.Array)
            {
                SpatialDebugLog.Instance.Log($"JSON Error: gridPoints must be an array, but was {token.Type}.", doLog, "red");
                return null;
            }

            var settings = new JsonSerializerSettings
            {
                Converters = new List<JsonConverter> { new Vector3Converter() }
            };

            return token.ToObject<List<GridPointData>>(JsonSerializer.Create(settings));
        }

        // Parse robot pose from markerData:
        // markerData = { robotLocalPos:{x,y,z}, robotLocalForward:{x,y,z} }
        // fallback keys: localPos / localForward
        private (Vector3? pos, Vector3? forward) ParseRobotPose(JToken markerDataToken)
        {
            if (markerDataToken == null) return (null, null);

            if (markerDataToken.Type == JTokenType.String)
            {
                var inner = markerDataToken.Value<string>();
                if (!string.IsNullOrWhiteSpace(inner))
                    markerDataToken = JToken.Parse(inner);
            }

            if (markerDataToken.Type != JTokenType.Object)
                return (null, null);

            var obj = (JObject)markerDataToken;

            JToken posToken =
                obj["robotLocalPos"] ?? obj["localPos"] ?? obj["markerLocalPos"];

            JToken fwdToken =
                obj["robotLocalForward"] ?? obj["localForward"] ?? obj["markerLocalForward"];

            Vector3? pos = ParseVector3Token(posToken);
            Vector3? fwd = ParseVector3Token(fwdToken);

            return (pos, fwd);
        }

        private Vector3? ParseVector3Token(JToken token)
        {
            if (token == null) return null;

            if (token.Type == JTokenType.String)
            {
                var inner = token.Value<string>();
                if (!string.IsNullOrWhiteSpace(inner))
                    token = JToken.Parse(inner);
            }

            if (token.Type != JTokenType.Object)
                return null;

            float x = token["x"] != null ? token["x"].Value<float>() : 0f;
            float y = token["y"] != null ? token["y"].Value<float>() : 0f;
            float z = token["z"] != null ? token["z"].Value<float>() : 0f;
            return new Vector3(x, y, z);
        }

        // =========================
        // Newtonsoft Vector3 Converters
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

        private class Vector3NullableConverter : JsonConverter<Vector3?>
        {
            public override void WriteJson(JsonWriter writer, Vector3? value, JsonSerializer serializer)
            {
                if (!value.HasValue)
                {
                    writer.WriteNull();
                    return;
                }

                Vector3 v = value.Value;
                writer.WriteStartObject();
                writer.WritePropertyName("x"); writer.WriteValue(v.x);
                writer.WritePropertyName("y"); writer.WriteValue(v.y);
                writer.WritePropertyName("z"); writer.WriteValue(v.z);
                writer.WriteEndObject();
            }

            public override Vector3? ReadJson(JsonReader reader, System.Type objectType, Vector3? existingValue, bool hasExistingValue, JsonSerializer serializer)
            {
                if (reader.TokenType == JsonToken.Null)
                    return null;

                JObject obj = JObject.Load(reader);
                float x = obj["x"] != null ? obj["x"].Value<float>() : 0f;
                float y = obj["y"] != null ? obj["y"].Value<float>() : 0f;
                float z = obj["z"] != null ? obj["z"].Value<float>() : 0f;
                return new Vector3(x, y, z);
            }
        }
    }
}
