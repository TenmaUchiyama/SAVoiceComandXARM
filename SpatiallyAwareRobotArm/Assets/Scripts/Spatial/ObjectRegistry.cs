using System;
using System.Collections.Generic;
using SA_XARM.SpatialRef.Data;
using UnityEngine;

namespace SA_XARM.SpatialRef.Spatial
{
    public class ObjectRegistry : MonoBehaviour
    {
        [Header("Grid Root")]
        [SerializeField] private Transform gridRoot;
        [SerializeField] private Vector3 defaultBoundingBoxSize = new Vector3(0.05f, 0.05f, 0.05f);

        public void RegisterFromGridConfig(List<global::Grid> _)
        {
            
        }

        public List<ObjectData> GetAll()
        {
            var result = new List<ObjectData>();
            Transform root = ResolveGridRoot();
            if (root == null) return result;

            global::Grid[] grids = root.GetComponentsInChildren<global::Grid>(true);
            for (int i = 0; i < grids.Length; i++)
            {
                global::Grid grid = grids[i];
                if (grid == null) continue;

                ObjectData data = BuildObjectData(grid);
                result.Add(data);
            }

            return result;
        }

        public GameObject FindHologram(string objectId)
        {
            if (string.IsNullOrWhiteSpace(objectId)) return null;
            Transform root = ResolveGridRoot();
            if (root == null) return null;

            global::Grid[] grids = root.GetComponentsInChildren<global::Grid>(true);
            for (int i = 0; i < grids.Length; i++)
            {
                global::Grid grid = grids[i];
                if (grid == null) continue;

                string gridObjectId = BuildObjectId(grid);
                if (string.Equals(gridObjectId, objectId, StringComparison.OrdinalIgnoreCase))
                {
                    return grid.gameObject;
                }
            }

            return null;
        }

        private Transform ResolveGridRoot()
        {
            if (gridRoot != null) return gridRoot;

            GameObject gridObject = GameObject.Find("Grid") ?? GameObject.Find("Grids");
            if (gridObject != null)
            {
                return gridObject.transform;
            }

            return null;
        }

        private ObjectData BuildObjectData(global::Grid grid)
        {
            Vector3 worldPosition = grid.transform.position;

            Vector3 boundingSize = ResolveBoundingSize(grid);

            return new ObjectData
            {
                id = BuildObjectId(grid),
                label = grid.gameObject.name,
                color = "unknown",
                position = Vec3.FromVector3(worldPosition),
                bounding_box = new BoundingBox
                {
                    center = Vec3.FromVector3(worldPosition),
                    size = Vec3.FromVector3(boundingSize)
                }
            };
        }

        private string BuildObjectId(global::Grid grid)
        {
            if (grid == null) return string.Empty;

            string nameId = grid.gameObject.name;
            if (!string.IsNullOrWhiteSpace(nameId))
            {
                return nameId;
            }

            (int x, int y) = grid.GetGridPosition();
            return $"grid_{x}_{y}";
        }

        private Vector3 ResolveBoundingSize(global::Grid grid)
        {
            if (grid == null) return defaultBoundingBoxSize;

            Renderer renderer = grid.GetComponentInChildren<Renderer>();
            if (renderer == null)
            {
                return defaultBoundingBoxSize;
            }

            return renderer.bounds.size;
        }
    }
}