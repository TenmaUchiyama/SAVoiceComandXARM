using UnityEngine;
using Microsoft.MixedReality.OpenXR;
using TMPro;
using System.Collections.Generic;
using System.IO;

public class QRGridCalibrator : MonoBehaviour
{
    [Header("Dependencies")]
    [SerializeField] private ARMarkerManager markerManager;
    [SerializeField] private Transform probeTransform; 

    [Header("QR Code Settings (Case Sensitive)")]
    [SerializeField] private string textForOrigin = "A"; 
    [SerializeField] private string textForAxis   = "B"; 

    [Header("UI")]
    [SerializeField] private TextMeshProUGUI statusText; // 既存の固定UIも残す
    [SerializeField] private GameObject visualFeedbackPrefab;

    // --- 内部データ ---
    private Vector3? cachedPosA = null; 
    private Vector3? cachedPosB = null;
    
    private bool calibrationStarted = false; 
    private Matrix4x4 worldToAnchorMatrix;
    private int recordIndex = 0;
    private List<GridPointData> recordedPoints = new List<GridPointData>();

    [System.Serializable]
    public class GridPointData
    {
        public int id;
        public Vector3 localPos;
    }

    private void Start()
    {
        // SpatialDebugLogを使用
        SpatialDebugLog.Instance.Log("[QRGridCalibrator] Initializing...");

        if (markerManager == null)
        {
            SpatialDebugLog.Instance.LogError("❌ ARMarkerManager is null!");
            return;
        }
        markerManager.markersChanged += OnMarkersChanged;
        
        UpdateUI_PreCalibration();
        SpatialDebugLog.Instance.Log("Ready. Waiting for markers...");
    }

    private void OnDestroy()
    {
        if (markerManager != null) markerManager.markersChanged -= OnMarkersChanged;
    }

    // --- 1. QRコード認識部分 ---
    private void OnMarkersChanged(ARMarkersChangedEventArgs args)
    {
        if (calibrationStarted) return;

        foreach (var added in args.added) ProcessMarker(added, "Added");
        foreach (var updated in args.updated) ProcessMarker(updated, "Updated");
    }

    private void ProcessMarker(ARMarker marker, string state)
    {
        string text = marker.GetDecodedString();

        // SpatialLogは見やすいので、検出ログを流してもOK
        // SpatialDebugLog.Instance.Log($"Marker ({state}): {text}", "gray");

        if (text == textForOrigin)
        {
            cachedPosA = marker.transform.position;
            // 成功ログ（緑）
            SpatialDebugLog.Instance.LogSuccess($"✅ Origin (A) Found! {cachedPosA}");
        }
        else if (text == textForAxis)
        {
            cachedPosB = marker.transform.position;
            // 成功ログ（緑）
            SpatialDebugLog.Instance.LogSuccess($"✅ Axis (B) Found! {cachedPosB}");
        }
        
        UpdateUI_PreCalibration();
    }

    // --- 2. メインループとキャリブレーション ---
    
    // ★ボタンから呼ぶ用（MRTKのInteractableからこれを呼ぶ想定）
    public void OnCalibrationAction()
    {
        if (!calibrationStarted)
        {
            TryStartCalibration();
        }
        else
        {
            RecordGridPoint();
        }
    }

    // キーボードデバッグ用
    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space))
        {
            OnCalibrationAction();
        }
    }

    private void TryStartCalibration()
    {
        SpatialDebugLog.Instance.Log("Attempting to lock...", "cyan");

        if (!cachedPosA.HasValue || !cachedPosB.HasValue)
        {
            // 警告は黄色で
            SpatialDebugLog.Instance.Log("❌ Cannot start. Need A & B.", "yellow");
            return;
        }

        Vector3 origin = cachedPosA.Value;
        Vector3 directionX = (cachedPosB.Value - origin).normalized;
        Vector3 up = Vector3.up;
        Vector3 directionZ = Vector3.Cross(directionX, up).normalized;
        Vector3 orthogUp = Vector3.Cross(directionZ, directionX).normalized;

        Quaternion rotation = Quaternion.LookRotation(directionZ, orthogUp);
        
        worldToAnchorMatrix = Matrix4x4.TRS(origin, rotation, Vector3.one).inverse;

        calibrationStarted = true;
        
        // 詳細な情報をログに出す
        SpatialDebugLog.Instance.Log("-----------------", "white");
        SpatialDebugLog.Instance.LogSuccess("🔒 System LOCKED");
        SpatialDebugLog.Instance.Log($"Origin: {origin}", "white");
        SpatialDebugLog.Instance.Log($"Rot: {rotation.eulerAngles}", "white");
        SpatialDebugLog.Instance.Log("-----------------", "white");

        UpdateUI_Recording();
    }

    private void RecordGridPoint()
    {
        if (recordIndex >= 16)
        {
            SpatialDebugLog.Instance.Log("All points done. Saving...", "cyan");
            SaveJson();
            return;
        }

        Vector3 currentWorldPos = probeTransform.position;
        Vector3 localPos = worldToAnchorMatrix.MultiplyPoint3x4(currentWorldPos);

        recordedPoints.Add(new GridPointData { id = recordIndex, localPos = localPos });

        // 記録ログ
        SpatialDebugLog.Instance.Log($"📍 Pt [{recordIndex}] : {localPos}", "white");

        if (visualFeedbackPrefab != null)
            Instantiate(visualFeedbackPrefab, currentWorldPos, Quaternion.identity);

        recordIndex++;
        UpdateUI_Recording();

        if (recordIndex >= 16) SaveJson();
    }

    // --- UI更新メソッド群 ---
    private void UpdateUI_PreCalibration()
    {
        if (statusText == null) return;
        string msg = "<b>Looking for Markers...</b>\n";
        msg += $"A: {(cachedPosA.HasValue ? "<color=green>OK</color>" : "<color=red>NO</color>")}\n";
        msg += $"B: {(cachedPosB.HasValue ? "<color=green>OK</color>" : "<color=red>NO</color>")}\n";
        if (cachedPosA.HasValue && cachedPosB.HasValue) msg += "\n<b>Press Button/Space to Lock</b>";
        statusText.text = msg;
    }

    private void UpdateUI_Recording()
    {
        if (statusText == null) return;
        if (recordIndex >= 16)
        {
            statusText.text = "<color=green>DONE! Saved.</color>";
            return;
        }
        int r = recordIndex / 4;
        int c = recordIndex % 4;
        statusText.text = $"<b>Record Grid</b>\nTarget: ({r}, {c})\nPress Button.";
    }

    private void SaveJson()
    {
        string json = JsonUtility.ToJson(new Serialization<GridPointData>(recordedPoints), true);
        string path = Path.Combine(Application.persistentDataPath, "qr_grid_config.json");
        
        SpatialDebugLog.Instance.Log($"💾 Saving to: {path}", "cyan");
        
        try
        {
            File.WriteAllText(path, json);
            SpatialDebugLog.Instance.LogSuccess("✅ Save SUCCESS!");
            // JSONの中身もログに出す（長い場合は適宜カット）
            SpatialDebugLog.Instance.Log("JSON content generated.", "gray");
        }
        catch (System.Exception e)
        {
            SpatialDebugLog.Instance.LogError($"❌ Save FAILED: {e.Message}");
        }
        
        if (statusText != null) statusText.text = $"Saved!\n{path}";
    }
}

[System.Serializable]
public class Serialization<T> {
    public List<T> target;
    public Serialization(List<T> target) { this.target = target; }
}