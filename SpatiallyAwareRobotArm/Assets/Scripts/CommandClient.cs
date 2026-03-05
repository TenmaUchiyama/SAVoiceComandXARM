using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using SA_XARM.Network.Request;
using UnityEngine.Events;

// =========================
// CommandClient.cs
// HoloLens(Unity) -> FastAPI /command
// - utterance (STT結果) + user pose + objects(with positions)
// - objects はシーン上の "Grids" 配下の子Transformから収集（world座標）
// =========================
public class CommandClient : MonoBehaviour
{
    [Header("Server")]
    [SerializeField]private string serverAddress = "192.168.108.164";
    [SerializeField] private int serverPort = 8080;
    [SerializeField] private string serverPath = "command";
    private string serverUrl = "";
    [SerializeField] private int timeoutSec = 10;

    [Header("Scene References")]
    [Tooltip("16個のグリッド(Box)が並んでいる親オブジェクト(例: Grids)")]
    [SerializeField] private Transform gridsRoot;

    [Header("User (Camera)")]
    [SerializeField] private Camera userCamera; // nullなら Camera.main を使う
    [SerializeField] private float fovDegOverride = -1f; // -1ならCamera.fieldOfViewを使う

    [Header("Options")]
    [Tooltip("非アクティブな子も送るならtrue")]
    [SerializeField] private bool includeInactive = false;

    [Tooltip("子オブジェクト名をそのまま id に使う（例: obj_00 など）")]
    [SerializeField] private bool useChildNameAsId = true;

[SerializeField] private Transform robotBaseTransform;
    

    public UnityEvent<CommandResponseDto> OnReceiveCommandResponse;

public string debugUtterance = "目の前の箱を一個とって";

    void Awake()
    {
        this.serverUrl  = $"http://{serverAddress}:{serverPort}/{serverPath}";
    }
    // =========================
    // Public API
    // =========================





    void Update()
    {
        if(Input.GetKeyDown(KeyCode.Space))
        {
            SendCommand(debugUtterance);
        }
    }
    public async void SendCommand(string utterance)
    {
        if (gridsRoot == null)
        {
            Debug.LogError("[CommandClient] gridsRoot is null. Assign 'Grids' transform in Inspector.");
            return;
        }

        if (userCamera == null)
        {
            userCamera = Camera.main;
            if (userCamera == null)
            {
                Debug.LogError("[CommandClient] userCamera is null and Camera.main not found.");
                return;
            }
        }

        if (XarmAppServerQueryRequester.Instance == null)
        {
            Debug.LogError("[CommandClient] XarmAppServerQueryRequester.Instance is null.");
            return;
        }

        // Build request
        var req = BuildRequest(utterance);
        string json = JsonConvert.SerializeObject(req, Formatting.None);

        Debug.Log($"[CommandClient] Sending command: {json}");

        Debug.Log($"Check null XarmAppServerQueryRequester.Instance: {XarmAppServerQueryRequester.Instance == null}");
        try
        {
            
            string response = await XarmAppServerQueryRequester.Instance.SendQuery(serverPath, json);
            Debug.Log("[CommandClient] Received response: " + response);
            LogStageLlmIO(response);
            if (OnReceiveCommandResponse != null)
            {
                CommandResponseDto responseDto = JsonConvert.DeserializeObject<CommandResponseDto>(response);
                OnReceiveCommandResponse.Invoke(responseDto);
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"[CommandClient] Failed to send command: {e.Message}");
        }
    }

    // =========================
    // Request/Response DTOs
    // =========================
    [Serializable]
    public class PoseDto
    {
        public float[] position; // [x,y,z]
        public float[] forward;  // [x,y,z]
        public float   fov_deg;
    }

    [Serializable]
    public class ObjectDto
    {
        public string  id;
        public float[] position; // [x,y,z]
    }

    [Serializable]
public class CommandRequestDto
{
    public string session_id;
    public long timestamp_ms;
    public string utterance;
    public PoseDto user;
    public RobotPoseDto robot;          // ← object じゃなくて型で持つのが安全
    public List<ObjectDto> objects;
}


    [Serializable]
    public class CommandResponseDto
    {
        public string status;
        public string target_id;
        public string reference_frame;
        public string explain;
        public object debug;
        public object llm_input;
        public object computed_features;
        public string reason;
    }


    [Serializable]
public class RobotPoseDto
{
    public float[] position; // [x,y,z]
    public float[] forward;  // [x,y,z]
}


private RobotPoseDto BuildRobotPoseDto()
{
    // ロボットがシーンに無いなら null にしてOK（server側は Optional）
    if (robotBaseTransform == null) return null;

    Vector3 p = robotBaseTransform.position;
    Vector3 f = robotBaseTransform.forward.normalized;

    return new RobotPoseDto
    {
        position = new float[] { p.x, p.y, p.z },
        forward  = new float[] { f.x, f.y, f.z },
    };
}


    // =========================
    // Core
    // =========================
    private CommandRequestDto BuildRequest(string utterance)
    {
        // user pose
        Vector3 camPos = userCamera.transform.position;
        Vector3 camFwd = userCamera.transform.forward.normalized;

        float fov = (fovDegOverride > 0f) ? fovDegOverride : userCamera.fieldOfView;

        var userPose = new PoseDto
        {
            position = new float[] { camPos.x, camPos.y, camPos.z },
            forward  = new float[] { camFwd.x, camFwd.y, camFwd.z },
            fov_deg  = fov
        };

        // objects from Grids children (world positions)
        var objects = CollectObjectsFromGrids(gridsRoot);

        var req = new CommandRequestDto
        {
            session_id = Guid.NewGuid().ToString("N"),
            timestamp_ms = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            utterance = utterance,
            user = userPose,
              robot         = BuildRobotPoseDto(),  
            objects = objects
        };

        return req;
    }

    private List<ObjectDto> CollectObjectsFromGrids(Transform root)
{
    var list = new List<ObjectDto>();

    foreach (Transform t in root) // ★ 直下の子だけ
    {
        // 非アクティブを除外したい場合
        if (!includeInactive && !t.gameObject.activeInHierarchy)
            continue;

        Vector3 p = t.position; // world座標
        string id = useChildNameAsId ? t.name : MakeFallbackId(t);

        list.Add(new ObjectDto
        {
            id = id,
            position = new float[] { p.x, p.y, p.z }
        });
    }

    // 念のためID順で安定化（デバッグ・再現性）
    list.Sort((a, b) => string.CompareOrdinal(a.id, b.id));

    Debug.Log($"[CommandClient] Collected objects (direct children only): {list.Count}");
    return list;
}


    private string MakeFallbackId(Transform t)
    {
        // 子の並び順でIDを生成（名前運用しない場合用）
        // 例: obj_00.. などにしたいならここを自分のルールに合わせて変えてOK
        int sibling = t.GetSiblingIndex();
        return $"obj_{sibling:D2}";
    }

    private void LogStageLlmIO(string responseJson)
    {
        if (string.IsNullOrWhiteSpace(responseJson))
        {
            return;
        }

        JObject root;
        try
        {
            root = JObject.Parse(responseJson);
        }
        catch
        {
            return;
        }

        for (int stage = 1; stage <= 3; stage++)
        {
            string inputText;
            string outputText;
            bool found = TryExtractStageInputOutput(root, stage, out inputText, out outputText);
            if (!found)
            {
                continue;
            }

            Debug.Log(
                $"======= Stage {stage} 入力 =======\n" +
                $"{inputText}\n" +
                "=====================\n" +
                $"=======Stage {stage} 出力=========\n" +
                $"{outputText}\n" +
                "====================="
            );
        }
    }

    private bool TryExtractStageInputOutput(JObject root, int stage, out string inputText, out string outputText)
    {
        inputText = string.Empty;
        outputText = string.Empty;

        JToken stageNode = FindStageNode(root, stage);
        if (stageNode != null)
        {
            JToken inToken = FindByCandidateKeys(stageNode, "input", "prompt", "llm_input", "request", "messages", "query");
            JToken outToken = FindByCandidateKeys(stageNode, "output", "response", "llm_output", "result", "answer", "text");

            inputText = TokenToReadableText(inToken);
            outputText = TokenToReadableText(outToken);
        }

        JToken flatInput = FindByCandidateKeys(
            root,
            $"stage{stage}_input",
            $"stage_{stage}_input",
            $"Stage{stage}Input",
            $"Stage{stage}_Input"
        );
        JToken flatOutput = FindByCandidateKeys(
            root,
            $"stage{stage}_output",
            $"stage_{stage}_output",
            $"Stage{stage}Output",
            $"Stage{stage}_Output"
        );

        if (string.IsNullOrEmpty(inputText))
        {
            inputText = TokenToReadableText(flatInput);
        }
        if (string.IsNullOrEmpty(outputText))
        {
            outputText = TokenToReadableText(flatOutput);
        }

        bool hasInput = !string.IsNullOrEmpty(inputText);
        bool hasOutput = !string.IsNullOrEmpty(outputText);
        if (!hasInput && !hasOutput)
        {
            return false;
        }

        if (!hasInput)
        {
            inputText = "(なし)";
        }
        if (!hasOutput)
        {
            outputText = "(なし)";
        }

        return true;
    }

    private JToken FindStageNode(JObject root, int stage)
    {
        string[] stageKeys = new string[]
        {
            $"stage{stage}",
            $"stage_{stage}",
            $"Stage{stage}",
            $"Stage {stage}",
            $"stage {stage}"
        };

        JToken[] containers = new JToken[]
        {
            root,
            root["llm_input"],
            root["debug"],
            root["llm"],
            root["stages"]
        };

        foreach (JToken container in containers)
        {
            if (container == null)
            {
                continue;
            }

            foreach (string key in stageKeys)
            {
                JToken hit = container[key];
                if (hit != null)
                {
                    return hit;
                }
            }
        }

        return null;
    }

    private JToken FindByCandidateKeys(JToken token, params string[] keys)
    {
        if (token == null || keys == null || keys.Length == 0)
        {
            return null;
        }

        if (token is JObject obj)
        {
            foreach (string key in keys)
            {
                JToken direct = obj[key];
                if (direct != null)
                {
                    return direct;
                }

                foreach (var prop in obj.Properties())
                {
                    if (string.Equals(prop.Name, key, StringComparison.OrdinalIgnoreCase))
                    {
                        return prop.Value;
                    }
                }
            }

            foreach (var prop in obj.Properties())
            {
                JToken nested = FindByCandidateKeys(prop.Value, keys);
                if (nested != null)
                {
                    return nested;
                }
            }
        }
        else if (token is JArray arr)
        {
            foreach (JToken item in arr)
            {
                JToken nested = FindByCandidateKeys(item, keys);
                if (nested != null)
                {
                    return nested;
                }
            }
        }

        return null;
    }

    private string TokenToReadableText(JToken token)
    {
        if (token == null || token.Type == JTokenType.Null)
        {
            return string.Empty;
        }

        if (token.Type == JTokenType.String)
        {
            return token.ToString();
        }

        return token.ToString(Formatting.Indented);
    }
}
