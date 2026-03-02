using System;
using System.Collections.Generic;
using SA_XARM.SpatialRef.Data;
using UnityEngine;

namespace SA_XARM.SpatialRef.Spatial
{
    public class SpatialContextProvider : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Camera mainCamera;
        [SerializeField] private Transform robotAnchor;
        [SerializeField] private ObjectRegistry objectRegistry;

        public UserPose GetUserPose()
        {
            var cam = mainCamera != null ? mainCamera : Camera.main;
            if (cam == null)
            {
                return new UserPose
                {
                    position = new Vec3(),
                    forward = new Vec3(0f, 0f, 1f),
                    up = new Vec3(0f, 1f, 0f)
                };
            }

            Vector3 worldPos = cam.transform.position;
            Vector3 worldFwd = cam.transform.forward;
            Vector3 worldUp = cam.transform.up;

            return new UserPose
            {
                position = Vec3.FromVector3(worldPos),
                forward = Vec3.FromVector3(worldFwd),
                up = Vec3.FromVector3(worldUp)
            };
        }

        public TableFrame GetTableFrame()
        {
            return new TableFrame
            {
                origin = new Vec3(0f, 0f, 0f),
                x_axis = new Vec3(1f, 0f, 0f),
                y_axis = new Vec3(0f, 1f, 0f),
                z_axis = new Vec3(0f, 0f, 1f)
            };
        }

        public RobotPose GetRobotPose()
        {
            if (robotAnchor == null)
            {
                return new RobotPose
                {
                    position = new Vec3(),
                    forward = new Vec3(0f, 0f, 1f)
                };
            }

            return new RobotPose
            {
                position = Vec3.FromVector3(robotAnchor.position),
                forward = Vec3.FromVector3(robotAnchor.forward)
            };
        }

        public List<ObjectData> GetObjects()
        {
            if (objectRegistry == null) return new List<ObjectData>();
            return objectRegistry.GetAll();
        }

        public SpatialReferenceRequest BuildRequest(string utteranceText, string language = "ja")
        {
            return new SpatialReferenceRequest
            {
                request_id = Guid.NewGuid().ToString(),
                timestamp = DateTime.UtcNow.ToString("o"),
                utterance = new Utterance
                {
                    text = utteranceText,
                    language = string.IsNullOrWhiteSpace(language) ? "ja" : language
                },
                user_pose = GetUserPose(),
                objects = GetObjects(),
                table_frame = GetTableFrame(),
                robot_pose = GetRobotPose()
            };
        }

    }
}