using System.Collections.Generic;
using UnityEngine;

namespace SA_XARM.WakeWord
{
    /// <summary>
    /// WakeWordManager is disabled to avoid conflict with DictationRecognizer.
    /// </summary>
    public class WakeWordManager : MonoBehaviour
    {
        // This component is intentionally left empty to remove dependency on KeywordRecognitionSubsystem.
        public void RegisterRuntime(string keyword, System.Action action)
        {
            // Do nothing
        }
    }

    [System.Serializable]
    public class WakeWordEntry
    {
        public string keyword;
        public UnityEngine.Events.UnityEvent onRecognized;
    }
}
