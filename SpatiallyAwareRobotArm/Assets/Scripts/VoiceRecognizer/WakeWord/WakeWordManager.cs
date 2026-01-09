


using System.Collections.Generic;
using UnityEngine;
using MixedReality.Toolkit;
using MixedReality.Toolkit.Subsystems;


namespace SA_XARM.WakeWord{
public class WakeWordManager : MonoBehaviour
{
    [Header("Wake Word Settings")]
    [SerializeField]
    private List<WakeWordEntry> wakeWords = new();

    private KeywordRecognitionSubsystem keywordSubsystem;

    void OnEnable()
    {
        Debug.Log("===== [WakeWordManager] OnEnable =====");

        keywordSubsystem =
            XRSubsystemHelpers.GetFirstRunningSubsystem<KeywordRecognitionSubsystem>();

        if (keywordSubsystem == null)
        {
            Debug.LogError("[WakeWordManager] ❌ KeywordRecognitionSubsystem NOT FOUND");
            DumpAllKeywordSubsystems();
            return;
        }

        Debug.Log("[WakeWordManager] ✅ KeywordRecognitionSubsystem FOUND");

        RegisterAllWakeWords();
    }

    void OnDisable()
    {
        Debug.Log("===== [WakeWordManager] OnDisable =====");
        UnregisterAll();
    }

    // ================================
    // Inspector 登録
    // ================================
    private void RegisterAllWakeWords()
    {
        foreach (var entry in wakeWords)
        {
            if (string.IsNullOrWhiteSpace(entry.keyword))
            {
                Debug.LogWarning("[WakeWordManager] Empty keyword skipped");
                continue;
            }

            var keywordEvent =
                keywordSubsystem.CreateOrGetEventForKeyword(entry.keyword);

            if (keywordEvent == null)
            {
                Debug.LogError($"[WakeWordManager] Failed to create event for {entry.keyword}");
                continue;
            }

            keywordEvent.AddListener(() =>
            {
                Debug.Log($"🔥 [WakeWord] \"{entry.keyword}\" recognized");
                entry.onRecognized?.Invoke();
            });

            Debug.Log($"[WakeWordManager] Registered WakeWord: \"{entry.keyword}\"");
        }
    }

    private void UnregisterAll()
    {
        foreach (var entry in wakeWords)
        {
            entry.onRecognized?.RemoveAllListeners();
        }
    }

    // ================================
    // コードからの追加（Inspector + Code 両立）
    // ================================
    public void RegisterRuntime(string keyword, System.Action action)
    {
        var unityEvent = new UnityEngine.Events.UnityEvent();
        unityEvent.AddListener(() => action());

        wakeWords.Add(new WakeWordEntry
        {
            keyword = keyword,
            onRecognized = unityEvent
        });

        // すでに Subsystem が動いているなら即登録
        if (keywordSubsystem != null)
        {
            var evt = keywordSubsystem.CreateOrGetEventForKeyword(keyword);
            evt.AddListener(() => unityEvent.Invoke());
        }
    }

    private void DumpAllKeywordSubsystems()
    {
        var subsystems = new List<KeywordRecognitionSubsystem>();
        SubsystemManager.GetSubsystems(subsystems);

        foreach (var s in subsystems)
        {
            Debug.Log($"Subsystem: running={s.running}, type={s.GetType().Name}");
        }
    }
}
}