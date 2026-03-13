using System;
using Newtonsoft.Json.Linq;
using SA_XARM.SpatialRef.Data;
using SA_XARM.SpatialRef.State;
using UnityEngine;

namespace SA_XARM.Network
{
    public class MessageRouter : MonoBehaviour
    {
        [SerializeField] private AppStateManager appStateManager;

        public void RouteMessage(string json)
        {
            if (string.IsNullOrWhiteSpace(json)) return;

            try
            {
                var root = JObject.Parse(json);
                string type = root.Value<string>("type");

                if (string.IsNullOrWhiteSpace(type) && root["payload"] != null)
                {
                    string payload = root.Value<string>("payload");
                    if (!string.IsNullOrWhiteSpace(payload))
                    {
                        var payloadObj = JObject.Parse(payload);
                        type = payloadObj.Value<string>("type");
                        root = payloadObj;
                    }
                }

                switch (type)
                {
                    case "spatial_reference_result":
                    {
                        var result = root.ToObject<SpatialReferenceResult>();
                        appStateManager?.OnResultReceived(result);
                        break;
                    }
                    case "robot_command":
                    {
                        var cmd = root.ToObject<RobotCommand>();
                        appStateManager?.OnRobotCommandReceived(cmd);
                        break;
                    }
                    case "server_error":
                    {
                        var error = root.ToObject<ServerErrorMessage>();
                        string msg = error != null
                            ? $"{error.code}: {error.message}"
                            : "Unknown server error";
                        if (SpatialDebugLog.Instance != null)
                        {
                            SpatialDebugLog.Instance.Log($"[MessageRouter] {msg}", true, "red");
                        }
                        break;
                    }
                    default:
                        if (SpatialDebugLog.Instance != null)
                        {
                            SpatialDebugLog.Instance.Log($"[MessageRouter] Unsupported type: {type}", true, "yellow");
                        }
                        break;
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[MessageRouter] Route failed: {ex.Message}");
            }
        }
    }
}