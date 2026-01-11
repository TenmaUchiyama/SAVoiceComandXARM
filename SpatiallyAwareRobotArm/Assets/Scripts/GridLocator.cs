using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

public class GridLocator : MonoBehaviour
{
     [Header("Anchor (manual / QR anchor)")]
    [SerializeField] private Transform qr_anchor;          // ← これをInspectorで入れる（基準）

    [Header("Spawn")]
    [SerializeField] private GameObject boxPrefab;         // ← 配置するPrefab
    [SerializeField] private bool spawnOnStart = false;    // 任意：起動時に配置したい場合

    [Header("JSON")]
    [SerializeField] private string jsonFileName = "grid_calibration.json"; // persistentDataPath内

    [Header("Options")]
    [SerializeField] private bool clearBeforeSpawn = true; // Spaceごとに再配置するならtrue
    [SerializeField] private bool preventDoubleSpawn = true;

    private bool spawnedOnce = false;
    private readonly List<GameObject> spawnedObjects = new List<GameObject>();

    // =========================
    // JSON classes (must match your saved format)
    // =========================
    [System.Serializable]
    private class QrAnchorData
    {
        public Vector3 worldPosition;
        public Quaternion worldRotation;
    }

    [System.Serializable]
    private class GridPointData
    {
        public int grid_x;
        public int grid_y;
        public Vector3 local_position;
    }

    [System.Serializable]
    private class CalibrationData
    {
        public QrAnchorData qr_anchor;
        public List<GridPointData> grid_points;
    }

    void Start()
    {
        if (spawnOnStart)
        {
            Spawn();
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space))
        {
            Spawn();
        }
    }

    private void Spawn()
    {
        if (qr_anchor == null)
        {
            Debug.LogError("[GridPlacerFromJson] qr_anchor is null. Assign it in Inspector.");
            return;
        }

        if (boxPrefab == null)
        {
            Debug.LogError("[GridPlacerFromJson] boxPrefab is null. Assign it in Inspector.");
            return;
        }

        if (preventDoubleSpawn && spawnedOnce)
        {
            Debug.Log("[GridPlacerFromJson] Already spawned once (preventDoubleSpawn=true).");
            return;
        }

       string path = Path.Combine(Application.dataPath, "CalibrationData/grid_calibration.json");
        if (!File.Exists(path))
        {
            Debug.LogError($"[GridPlacerFromJson] JSON not found: {path}");
            return;
        }

        string json = File.ReadAllText(path);
        CalibrationData data = JsonUtility.FromJson<CalibrationData>(json);

        if (data == null || data.grid_points == null || data.grid_points.Count == 0)
        {
            Debug.LogError("[GridPlacerFromJson] Invalid JSON or grid_points is empty.");
            return;
        }

        if (clearBeforeSpawn)
        {
            ClearSpawned();
        }

        Vector3 anchorPos = qr_anchor.position;

        foreach (var p in data.grid_points)
        {
            Vector3 worldPos = new Vector3(
                anchorPos.x + p.local_position.x,
                anchorPos.y, 
                anchorPos.z + p.local_position.z
            );

            GameObject go = Instantiate(boxPrefab, worldPos, Quaternion.identity);
            go.name = $"GridBox_{p.grid_x}_{p.grid_y}";
            spawnedObjects.Add(go);
        }

        spawnedOnce = true;
        Debug.Log($"[GridPlacerFromJson] Spawned {data.grid_points.Count} objects using anchor '{qr_anchor.name}'.");
    }

    private void ClearSpawned()
    {
        for (int i = 0; i < spawnedObjects.Count; i++)
        {
            if (spawnedObjects[i] != null)
                Destroy(spawnedObjects[i]);
        }
        spawnedObjects.Clear();
        spawnedOnce = false;
    }
}
