using UnityEngine;
using MixedReality.Toolkit;
using MixedReality.Toolkit.Subsystems;
using System;
using UnityEngine.Events;





namespace SA_XARM.WakeWord{



 [Serializable]
    public class WakeWordEntry
    {
        [Tooltip("認識する WakeWord")]
        public string keyword;

        [Tooltip("WakeWord が認識されたときに呼ばれるイベント")]
        public UnityEvent onRecognized;
    }



public class WakeWordKeyword : MonoBehaviour
{

   


    
    private KeywordRecognitionSubsystem keywordSubsystem;
    private UnityEngine.Events.UnityEvent keywordEvent;

    private const string Keyword = "こんにちは";

    void OnEnable()
    {
        Debug.Log("===== [WakeWordKeyword] OnEnable =====");

        // ① 実行環境の確認
#if UNITY_EDITOR
        Debug.Log("[WakeWordKeyword] Running in UNITY_EDITOR");
#else
        Debug.Log("[WakeWordKeyword] Running on DEVICE (not Editor)");
#endif

        // ② Subsystem 取得
        keywordSubsystem =
            XRSubsystemHelpers.GetFirstRunningSubsystem<KeywordRecognitionSubsystem>();

        if (keywordSubsystem == null)
        {
            Debug.LogError("[WakeWordKeyword] ❌ KeywordRecognitionSubsystem NOT FOUND or NOT RUNNING");
            DumpAllKeywordSubsystems();
            return;
        }

        Debug.Log("[WakeWordKeyword] ✅ KeywordRecognitionSubsystem FOUND");
        Debug.Log($"[WakeWordKeyword] Subsystem running = {keywordSubsystem.running}");

        // ③ キーワードイベント取得／作成
        keywordEvent = keywordSubsystem.CreateOrGetEventForKeyword(Keyword);

        if (keywordEvent == null)
        {
            Debug.LogError("[WakeWordKeyword] ❌ CreateOrGetEventForKeyword returned NULL");
            return;
        }

        Debug.Log($"[WakeWordKeyword] ✅ Keyword event registered for \"{Keyword}\"");

        // ④ リスナー登録
        keywordEvent.AddListener(OnKeywordRecognized);

        Debug.Log("[WakeWordKeyword] Listener added");
        Debug.Log("===== [WakeWordKeyword] Ready =====");
    }

    void OnDisable()
    {
        Debug.Log("===== [WakeWordKeyword] OnDisable =====");

        if (keywordEvent != null)
        {
            keywordEvent.RemoveListener(OnKeywordRecognized);
            Debug.Log("[WakeWordKeyword] Listener removed");
        }
    }

    private void OnKeywordRecognized()
    {
        Debug.Log("🔥🔥🔥 [WakeWordKeyword] KEYWORD RECOGNIZED: こんにちは 🔥🔥🔥");
    }

    /// <summary>
    /// プロジェクト内に存在する KeywordRecognitionSubsystem を全部出す
    /// （running でない＝Editor など）
    /// </summary>
    private void DumpAllKeywordSubsystems()
    {
        Debug.Log("[WakeWordKeyword] Dumping all KeywordRecognitionSubsystem descriptors:");

        var subsystems = new System.Collections.Generic.List<KeywordRecognitionSubsystem>();
        SubsystemManager.GetSubsystems(subsystems);

        if (subsystems.Count == 0)
        {
            Debug.Log("[WakeWordKeyword] No KeywordRecognitionSubsystem instances exist");
            return;
        }

        foreach (var s in subsystems)
        {
            Debug.Log(
                $"[WakeWordKeyword] Subsystem instance: running={s.running}, type={s.GetType().Name}");
        }
    }
}
}