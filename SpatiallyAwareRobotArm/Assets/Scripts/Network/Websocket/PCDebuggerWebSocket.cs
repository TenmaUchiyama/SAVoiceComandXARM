using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace SA_XARM.Network.Websocket
{
    [Serializable]
    public class PcDebugPersistentListRequest
    {
        public string request_id;
        public bool recursive;
    }

    [Serializable]
    public class PcDebugPersistentListResponse
    {
        public string request_id;
        public bool success;
        public string base_path;
        public List<string> files;
        public List<string> directories;
        public string error;
    }

    [Serializable]
    public class PcDebugReadJsonRequest
    {
        public string request_id;
        public string relative_path;
    }

    [Serializable]
    public class PcDebugReadJsonResponse
    {
        public string request_id;
        public bool success;
        public string relative_path;
        public string content;
        public string error;
    }

    public class PCDebuggerWebSocket : MonoBehaviour
    {
        [Header("WebSocket Event IDs")]
        [SerializeField] private string listRequestEventId = "pc_debug_persistent_list_request";
        [SerializeField] private string listResponseEventId = "pc_debug_persistent_list_response";
        [SerializeField] private string readJsonRequestEventId = "pc_debug_read_json_request";
        [SerializeField] private string readJsonResponseEventId = "pc_debug_read_json_response";

        [Header("Settings")]
        [SerializeField] private bool autoSubscribeOnEnable = true;

        private WebSocketManager _webSocketManager;

        private void Start()
        {
            SafeLog("[PCDebuggerWS] Initialized.");
            if (!autoSubscribeOnEnable) return;
            Subscribe();
        }

        private void OnDisable()
        {
            if (!autoSubscribeOnEnable) return;
            Unsubscribe();
        }

        public void Subscribe()
        {
            _webSocketManager = ResolveManager();
            if (_webSocketManager == null)
            {
                SafeLogError("[PCDebuggerWS] WebSocketManager is not available.");
                return;
            }

            _webSocketManager.On<PcDebugPersistentListRequest>(listRequestEventId, OnListRequestReceived);
            _webSocketManager.On<PcDebugReadJsonRequest>(readJsonRequestEventId, OnReadJsonRequestReceived);
            SafeLog("[PCDebuggerWS] Subscribed request handlers.", "cyan");
        }

        public void Unsubscribe()
        {
            var manager = ResolveManager();
            if (manager == null) return;

            manager.Off(listRequestEventId);
            manager.Off(readJsonRequestEventId);
        }

        private void OnListRequestReceived(PcDebugPersistentListRequest request)
        {
            var response = new PcDebugPersistentListResponse
            {
                request_id = request?.request_id,
                success = false,
                files = new List<string>(),
                directories = new List<string>(),
                base_path = Application.persistentDataPath,
                error = null
            };

            try
            {
                string basePath = Application.persistentDataPath;
                bool recursive = request != null && request.recursive;
                SearchOption searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;

                foreach (string dirPath in Directory.GetDirectories(basePath, "*", searchOption))
                {
                    response.directories.Add(ToRelativePath(basePath, dirPath));
                }

                foreach (string filePath in Directory.GetFiles(basePath, "*", searchOption))
                {
                    response.files.Add(ToRelativePath(basePath, filePath));
                }

                response.success = true;
            }
            catch (Exception ex)
            {
                response.error = ex.Message;
                SafeLogError($"[PCDebuggerWS] Failed to list persistentDataPath: {ex.Message}");
            }

            Send(listResponseEventId, response);
        }

        private void OnReadJsonRequestReceived(PcDebugReadJsonRequest request)
        {
            var response = new PcDebugReadJsonResponse
            {
                request_id = request?.request_id,
                success = false,
                relative_path = request?.relative_path,
                content = null,
                error = null
            };

            if (request == null || string.IsNullOrWhiteSpace(request.relative_path))
            {
                response.error = "relative_path is required.";
                Send(readJsonResponseEventId, response);
                return;
            }

            try
            {
                if (!TryResolveSafePath(Application.persistentDataPath, request.relative_path, out string fullPath, out string normalizedRelativePath, out string pathError))
                {
                    response.error = pathError;
                    Send(readJsonResponseEventId, response);
                    return;
                }

                if (!normalizedRelativePath.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
                {
                    response.error = "Only .json files are supported.";
                    Send(readJsonResponseEventId, response);
                    return;
                }

                if (!File.Exists(fullPath))
                {
                    response.error = "File not found.";
                    Send(readJsonResponseEventId, response);
                    return;
                }

                response.relative_path = normalizedRelativePath;
                response.content = File.ReadAllText(fullPath);
                response.success = true;
            }
            catch (Exception ex)
            {
                response.error = ex.Message;
                SafeLogError($"[PCDebuggerWS] Failed to read json file: {ex.Message}");
            }

            Send(readJsonResponseEventId, response);
        }

        private void Send<T>(string eventId, T payload)
        {
            var manager = ResolveManager();
            if (manager == null || !manager.IsConnected)
            {
                SafeLogError($"[PCDebuggerWS] Cannot send '{eventId}' because WebSocket is not connected.");
                return;
            }

            manager.Send(eventId, payload);
        }

        private WebSocketManager ResolveManager()
        {
            if (_webSocketManager != null) return _webSocketManager;
            _webSocketManager = WebSocketManager.Instance;
            return _webSocketManager;
        }

        private static string ToRelativePath(string basePath, string targetPath)
        {
            string baseFullPath = Path.GetFullPath(basePath);
            if (!baseFullPath.EndsWith(Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal))
            {
                baseFullPath += Path.DirectorySeparatorChar;
            }

            Uri baseUri = new Uri(baseFullPath);
            Uri targetUri = new Uri(Path.GetFullPath(targetPath));
            string relative = Uri.UnescapeDataString(baseUri.MakeRelativeUri(targetUri).ToString());
            return relative.Replace('\\', '/');
        }

        private static bool TryResolveSafePath(string basePath, string relativePath, out string fullPath, out string normalizedRelativePath, out string error)
        {
            fullPath = null;
            normalizedRelativePath = null;
            error = null;

            string sanitized = relativePath.Replace('\\', '/').Trim();
            while (sanitized.StartsWith("/", StringComparison.Ordinal))
            {
                sanitized = sanitized.Substring(1);
            }

            if (string.IsNullOrWhiteSpace(sanitized))
            {
                error = "relative_path is empty.";
                return false;
            }

            if (Path.IsPathRooted(sanitized))
            {
                error = "absolute path is not allowed.";
                return false;
            }

            string baseFullPath = Path.GetFullPath(basePath);
            string candidatePath = Path.GetFullPath(Path.Combine(baseFullPath, sanitized));

            string baseWithSep = baseFullPath.EndsWith(Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal)
                ? baseFullPath
                : baseFullPath + Path.DirectorySeparatorChar;

            bool isInside = candidatePath.StartsWith(baseWithSep, StringComparison.OrdinalIgnoreCase)
                || string.Equals(candidatePath, baseFullPath, StringComparison.OrdinalIgnoreCase);

            if (!isInside)
            {
                error = "path traversal is not allowed.";
                return false;
            }

            fullPath = candidatePath;
            normalizedRelativePath = ToRelativePath(baseFullPath, candidatePath);
            return true;
        }

        private static void SafeLog(string message, string color = "white")
        {
            if (SpatialDebugLog.Instance != null)
            {
                SpatialDebugLog.Instance.Log(message, true, color);
                return;
            }

            Debug.Log(message);
        }

        private static void SafeLogError(string message)
        {
            if (SpatialDebugLog.Instance != null)
            {
                SpatialDebugLog.Instance.LogError(message, true);
                return;
            }

            Debug.LogError(message);
        }
    }
}