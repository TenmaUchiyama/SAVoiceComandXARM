using System;
using System.Collections.Generic;
using SA_XARM.SpatialRef.Data;
using UnityEngine;

namespace SA_XARM.SpatialRef.Spatial
{
    public class ObjectRegistry : MonoBehaviour
    {
        [Header("Spatial Object Root")]
        [SerializeField] private Transform spatialObjectRoot;

        public void RegisterFromGridConfig(List<SpatialObject> _)
        {
            
        }

        public List<ObjectData> GetAll()
        {
            var result = new List<ObjectData>();
            Transform root = ResolveSpatialObjectRoot();
            if (root == null)
            {
                Debug.LogWarning("[ObjectRegistry] spatialObjectRoot is not resolved.");
                return result;
            }

            SpatialObject[] spatialObjects = root.GetComponentsInChildren<SpatialObject>(true);
            for (int i = 0; i < spatialObjects.Length; i++)
            {
                SpatialObject spatialObject = spatialObjects[i];
                if (spatialObject == null) continue;

                ObjectData data = BuildObjectData(spatialObject);
                result.Add(data);
            }

            if (result.Count == 0)
            {
                int fallbackIndex = 0;
                for (int i = 0; i < root.childCount; i++)
                {
                    Transform child = root.GetChild(i);
                    if (child == null) continue;

                    if (!child.gameObject.activeInHierarchy && !child.gameObject.activeSelf) continue;

                    fallbackIndex++;
                    result.Add(new ObjectData
                    {
                        id = string.IsNullOrWhiteSpace(child.name) ? $"fallback_object_{fallbackIndex}" : child.name,
                        label = "unknown",
                        color = "unknown",
                        position = Vec3.FromVector3(child.position)
                    });
                }

                Debug.LogWarning($"[ObjectRegistry] SpatialObject component not found under '{root.name}'. Fallback objects collected: {result.Count}");
            }
            else
            {
                Debug.Log($"[ObjectRegistry] Collected SpatialObjects: {result.Count} (root={root.name})");
            }

            return result;
        }

        public GameObject FindHologram(string objectId)
        {
            if (string.IsNullOrWhiteSpace(objectId)) return null;
            Transform root = ResolveSpatialObjectRoot();
            if (root == null) return null;

            SpatialObject[] spatialObjects = root.GetComponentsInChildren<SpatialObject>(true);
            for (int i = 0; i < spatialObjects.Length; i++)
            {
                SpatialObject spatialObject = spatialObjects[i];
                if (spatialObject == null) continue;

                string spatialObjectId = BuildObjectId(spatialObject);
                if (string.Equals(spatialObjectId, objectId, StringComparison.OrdinalIgnoreCase))
                {
                    return spatialObject.gameObject;
                }
            }

            return null;
        }

        private Transform ResolveSpatialObjectRoot()
        {
            if (spatialObjectRoot != null) return spatialObjectRoot;

            GameObject spatialObjects = GameObject.Find("SpatialObjects") ?? GameObject.Find("SpatialObject");
            if (spatialObjects != null)
            {
                return spatialObjects.transform;
            }

            return null;
        }

        private ObjectData BuildObjectData(SpatialObject spatialObject)
        {
            Vector3 worldPosition = spatialObject.transform.position;

            return new ObjectData
            {
                id = BuildObjectId(spatialObject),
                label = spatialObject.GetLabel(),
                color = spatialObject.GetColorName(),
                position = Vec3.FromVector3(worldPosition)
            };
        }

        private string BuildObjectId(SpatialObject spatialObject)
        {
            if (spatialObject == null) return string.Empty;

            string nameId = spatialObject.GetObjectId();
            if (!string.IsNullOrWhiteSpace(nameId))
            {
                return nameId;
            }

            (int x, int y) = spatialObject.GetGridPosition();
            return $"spatial_object_{x}_{y}";
        }




        public void SetVisualAll(bool visible)
        {
            Transform root = ResolveSpatialObjectRoot();
            if (root == null)
            {
                Debug.LogWarning("[ObjectRegistry] spatialObjectRoot is not resolved.");
                return;
            }

            SpatialObject[] spatialObjects = root.GetComponentsInChildren<SpatialObject>(true);
            for (int i = 0; i < spatialObjects.Length; i++)
            {
                spatialObjects[i]?.SetVisualize(visible);
            }

            Debug.Log($"[ObjectRegistry] SetVisualAll({visible}) applied to {spatialObjects.Length} objects.");
        }

        public void UnvisuaizeAll()
        {
            SetVisualAll(false);
        }

    }
}