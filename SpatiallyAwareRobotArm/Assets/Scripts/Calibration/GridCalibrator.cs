using UnityEngine;
using System.Collections.Generic;
using System.IO;
using TMPro;

public class GridCalibrator : MonoBehaviour
{
    [Header("Movable Object (grab & move this)")]
    [SerializeField] private Transform probeTransform; // つまんで動かすCube等（アンカー確定もグリッド記録もこれでやる）

    [Header("Optional visual feedback prefab (pin)")]
    [SerializeField] private GameObject visualFeedbackPrefab;

    [Header("Grid")]
    [SerializeField] private int gridSize = 4;

    [Header("Anchor Settings (Scale is ALWAYS treated as 1)")]
    [SerializeField] private bool useProbeRotationAsAnchor = false;
    // false: 位置だけ保存（回転はidentity。軸はワールド基準）
    // true : probeの回転も保存（ローカル軸も手で決める）
    [SerializeField] private bool forceAnchorScaleOne = true; // アンカー確定時に probeTransform の scale を 1 に戻す（任意）

    [Header("UI (Debug Dialog)")]
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private Renderer statusPanel;
    [SerializeField] private float toastSeconds = 1.2f;

    // ---- internal ----
    private bool anchorSaved = false;
    private Vector3 anchorPos;
    private Quaternion anchorRot;
    private int index = 0;

    private float toastUntil = 0f;

    private enum ToastType { Info, Success, Error }

    [System.Serializable]
    private class AnchorData
    {
        public Vector3 worldPosition;
        public Quaternion worldRotation;
    }

    [System.Serializable]
    private class GridPointData
    {
        public int grid_x;
        public int grid_y;
        public Vector3 local_position; // Anchor基準ローカル座標（※scaleを含めない）
    }

    [System.Serializable]
    private class CalibrationData
    {
        public AnchorData anchor = new AnchorData();
        public List<GridPointData> grid_points = new List<GridPointData>();
    }

    private CalibrationData data = new CalibrationData();

    void Start()
    {
        UpdateStatusUI();
        ShowToast("Ready. Move cube to Anchor position, then press Space.", ToastType.Info);
    }

    void Update()
    {
        if (toastUntil > 0f && Time.time >= toastUntil)
        {
            toastUntil = 0f;
            UpdateStatusUI();
        }

        if (!Input.GetKeyDown(KeyCode.Space))
            return;

        if (!anchorSaved)
        {
            if (SaveAnchorFromProbe())
                ShowToast("Anchor marked (scale treated as 1)!", ToastType.Success);
            return;
        }

        int total = gridSize * gridSize;

        if (index < total)
        {
            if (RecordNextPoint())
                ShowToast("Point recorded!", ToastType.Success);
            return;
        }

        if (SaveToJson(out string path))
            ShowToast($"JSON saved:\n{path}", ToastType.Success);
    }

    // =========================
    // Phase 0: Save Anchor (Manual by cube)
    // =========================
    private bool SaveAnchorFromProbe()
    {
        if (probeTransform == null)
        {
            ShowToast("ERROR: probeTransform is null (assign your movable cube)", ToastType.Error);
            return false;
        }

        if (forceAnchorScaleOne)
        {
            // 計算用アンカーは scale=1 が前提。掴み操作でscaleが入っていたら戻す。
            probeTransform.localScale = Vector3.one;
        }

        anchorPos = probeTransform.position;
        anchorRot = useProbeRotationAsAnchor ? probeTransform.rotation : Quaternion.identity;

        data.anchor.worldPosition = anchorPos;
        data.anchor.worldRotation = anchorRot;

        anchorSaved = true;
        index = 0;
        data.grid_points.Clear();

        UpdateStatusUI();
        return true;
    }

    // =========================
    // Phase 1: Record Grid Points
    // =========================
    private bool RecordNextPoint()
    {
        if (probeTransform == null)
        {
            ShowToast("ERROR: probeTransform is null (assign your movable cube)", ToastType.Error);
            return false;
        }

        int total = gridSize * gridSize;
        if (index >= total)
        {
            ShowToast("All points already recorded.", ToastType.Info);
            return false;
        }

        int x = index / gridSize;
        int y = index % gridSize;

        Vector3 worldPos = probeTransform.position;

        // ---- scale=1前提のローカル化（scaleは絶対に入れない） ----
        // local = inverse(R) * (world - anchorPos)
        Vector3 localPos = Quaternion.Inverse(anchorRot) * (worldPos - anchorPos);

        data.grid_points.Add(new GridPointData
        {
            grid_x = x,
            grid_y = y,
            local_position = localPos
        });

        if (visualFeedbackPrefab != null)
            Instantiate(visualFeedbackPrefab, worldPos, Quaternion.identity);

        index++;
        UpdateStatusUI();

        if (index >= total)
            ShowToast("All points recorded. Press Space to save JSON.", ToastType.Info);

        return true;
    }

    // =========================
    // Phase 2: Save JSON
    // =========================
    private bool SaveToJson(out string savedPath)
    {
        savedPath = "";
        try
        {
            string path = Path.Combine(Application.dataPath, "CalibrationData/grid_calibration.json");
            string json = JsonUtility.ToJson(data, true);
            File.WriteAllText(path, json);

            savedPath = path;
            UpdateStatusUI();
            return true;
        }
        catch (System.Exception e)
        {
            ShowToast($"ERROR saving JSON:\n{e.Message}", ToastType.Error);
            return false;
        }
    }

    // =========================
    // UI helpers
    // =========================
    private void ShowToast(string message, ToastType type)
    {
        toastUntil = Time.time + toastSeconds;
        ApplyPanelColor(type);
        ApplyText(BuildBaseStatus() + "\n\n" + $"<b>{message}</b>");
    }

    private void UpdateStatusUI()
    {
        ApplyPanelColor(ToastType.Info);
        ApplyText(BuildBaseStatus());
    }

    private string BuildBaseStatus()
    {
        int total = gridSize * gridSize;

        if (!anchorSaved)
        {
            return
                "<b>Grid Calibrator</b>\n" +
                "Step: <b>Mark Anchor (Manual)</b>\n" +
                "Action: Move cube to anchor position, then press <b>Space</b>.\n" +
                $"Anchor rotation mode: <b>{(useProbeRotationAsAnchor ? "Use Cube Rotation" : "World Axes (identity)")}</b>\n" +
                "Note: <b>Scale is treated as 1</b>\n";
        }

        if (index < total)
        {
            int x = index / gridSize;
            int y = index % gridSize;

            return
                "<b>Grid Calibrator</b>\n" +
                "Step: <b>Record Grid Points</b>\n" +
                $"Progress: <b>{index}/{total}</b>\n" +
                $"Next: <b>({x},{y})</b>\n" +
                "Action: Move cube, then press <b>Space</b>.\n" +
                "Note: <b>Scale is ignored</b>\n";
        }

        return
            "<b>Grid Calibrator</b>\n" +
            "Step: <b>Save JSON</b>\n" +
            $"Progress: <b>{index}/{total}</b> (done)\n" +
            "Action: Press <b>Space</b> to save JSON.\n";
    }

    private void ApplyText(string s)
    {
        if (statusText == null) return;
        statusText.text = s;
    }

    private void ApplyPanelColor(ToastType type)
    {
        if (statusPanel == null || statusPanel.material == null) return;

        switch (type)
        {
            case ToastType.Success:
                statusPanel.material.color = new Color(0.2f, 0.6f, 0.2f, 1f);
                break;
            case ToastType.Error:
                statusPanel.material.color = new Color(0.7f, 0.2f, 0.2f, 1f);
                break;
            default:
                statusPanel.material.color = new Color(0.15f, 0.15f, 0.15f, 1f);
                break;
        }
    }
}
