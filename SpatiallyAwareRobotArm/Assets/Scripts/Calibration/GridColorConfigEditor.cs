using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using UnityEngine;

namespace SA_XARM.Calibration
{
    [System.Serializable]
    public class GridColorEditEntry
    {
        public int gridX;
        public int gridY;
        public string color = "unknown";
    }

    public class GridColorConfigEditor : MonoBehaviour
    {
        [SerializeField] private string jsonFileName = "qr_grid_config.json";
        [SerializeField] private List<GridColorEditEntry> colorEntries = new List<GridColorEditEntry>();

        [ContextMenu("Load Entries From JSON")]
        public void LoadEntriesFromJson()
        {
            string path = Path.Combine(Application.persistentDataPath, jsonFileName);
            if (!File.Exists(path))
            {
                Debug.LogWarning($"[GridColorConfigEditor] JSON not found: {path}");
                return;
            }

            var points = LoadGridPoints(path);
            if (points == null) return;

            colorEntries.Clear();
            for (int i = 0; i < points.Count; i++)
            {
                var p = points[i];
                colorEntries.Add(new GridColorEditEntry
                {
                    gridX = p.gridX,
                    gridY = p.gridY,
                    color = string.IsNullOrWhiteSpace(p.color) ? "unknown" : p.color
                });
            }

            Debug.Log($"[GridColorConfigEditor] Loaded {colorEntries.Count} entries from {path}");
        }

        [ContextMenu("Apply Entries And Save JSON")]
        public void ApplyEntriesAndSaveJson()
        {
            string path = Path.Combine(Application.persistentDataPath, jsonFileName);
            if (!File.Exists(path))
            {
                Debug.LogWarning($"[GridColorConfigEditor] JSON not found: {path}");
                return;
            }

            var points = LoadGridPoints(path);
            if (points == null) return;

            var map = new Dictionary<string, string>();
            for (int i = 0; i < colorEntries.Count; i++)
            {
                var e = colorEntries[i];
                if (e == null) continue;
                map[$"{e.gridX}:{e.gridY}"] = string.IsNullOrWhiteSpace(e.color) ? "unknown" : e.color;
            }

            for (int i = 0; i < points.Count; i++)
            {
                var p = points[i];
                if (p == null) continue;
                string key = $"{p.gridX}:{p.gridY}";
                if (map.TryGetValue(key, out var color))
                {
                    p.color = color;
                }
                else if (string.IsNullOrWhiteSpace(p.color))
                {
                    p.color = "unknown";
                }
            }

            var settings = new JsonSerializerSettings
            {
                Formatting = Formatting.Indented,
                MissingMemberHandling = MissingMemberHandling.Ignore,
                NullValueHandling = NullValueHandling.Ignore
            };

            string json = JsonConvert.SerializeObject(points, settings);
            File.WriteAllText(path, json);
            Debug.Log($"[GridColorConfigEditor] Saved color-updated JSON: {path}");
        }

        private List<GridPointData> LoadGridPoints(string path)
        {
            try
            {
                string json = File.ReadAllText(path);
                var settings = new JsonSerializerSettings
                {
                    Formatting = Formatting.None,
                    MissingMemberHandling = MissingMemberHandling.Ignore,
                    NullValueHandling = NullValueHandling.Ignore
                };

                var points = JsonConvert.DeserializeObject<List<GridPointData>>(json, settings);
                if (points == null)
                {
                    Debug.LogWarning("[GridColorConfigEditor] JSON parse returned null");
                    return null;
                }

                return points;
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"[GridColorConfigEditor] Failed to load JSON: {ex.Message}");
                return null;
            }
        }
    }
}