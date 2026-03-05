using System.Collections;
using SA_XARM.SpatialRef.Data;
using UnityEngine;

namespace SA_XARM.SpatialRef.State
{
    public class UserBehaviorSimulator : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private AppStateManager appStateManager;

        [Header("Utterance")]
        [TextArea(2, 4)]
        [SerializeField] private string utteranceText = "目の前の箱を取って";

        [Header("Confirmation")]
        [SerializeField] private bool autoConfirmOnResult = true;
        [SerializeField] private float confirmationDelaySeconds = 0.2f;
        [SerializeField] private string targetObjectIdOverride = string.Empty;
        [TextArea(2, 4)]
        [SerializeField] private string feedbackUtteranceText = "はい";

        [Header("Auto Run")]
        [SerializeField] private bool runScenarioOnEnable = false;

        private bool _armedSingleAutoConfirm;
        private Coroutine _confirmRoutine;

        private void Reset()
        {
            appStateManager = FindObjectOfType<AppStateManager>();
        }

        private void OnEnable()
        {
            TryAutoBind();
            SubscribeEvents();

            if (runScenarioOnEnable)
            {
                RunUtteranceThenAutoConfirmOnce();
            }
        }

        private void OnDisable()
        {
            UnsubscribeEvents();

            if (_confirmRoutine != null)
            {
                StopCoroutine(_confirmRoutine);
                _confirmRoutine = null;
            }

            _armedSingleAutoConfirm = false;
        }

        public void SendUtterance()
        {
            if (!TryAutoBind()) return;

            if (string.IsNullOrWhiteSpace(utteranceText))
            {
                Debug.LogWarning("[UserBehaviorSimulator] utteranceText is empty.");
                return;
            }

            appStateManager.OnUtteranceReceived(utteranceText);
        }

        public void SendFeedback()
        {
            if (!TryAutoBind()) return;
            appStateManager.OnUserFeedback(feedbackUtteranceText, targetObjectIdOverride);
        }

        public void RunUtteranceThenAutoConfirmOnce()
        {
            _armedSingleAutoConfirm = true;
            SendUtterance();
        }

        private void OnResultUpdated(SpatialReferenceResult result)
        {
            bool shouldAutoConfirm = autoConfirmOnResult || _armedSingleAutoConfirm;
            if (!shouldAutoConfirm) return;

            if (_confirmRoutine != null)
            {
                StopCoroutine(_confirmRoutine);
            }

            _confirmRoutine = StartCoroutine(SendConfirmationDelayed());
        }

        private IEnumerator SendConfirmationDelayed()
        {
            if (confirmationDelaySeconds > 0f)
            {
                yield return new WaitForSeconds(confirmationDelaySeconds);
            }

            SendFeedback();
            _armedSingleAutoConfirm = false;
            _confirmRoutine = null;
        }

        private void SubscribeEvents()
        {
            if (appStateManager == null) return;
            appStateManager.OnResultUpdated += OnResultUpdated;
        }

        private void UnsubscribeEvents()
        {
            if (appStateManager == null) return;
            appStateManager.OnResultUpdated -= OnResultUpdated;
        }

        private bool TryAutoBind()
        {
            if (appStateManager != null) return true;

            appStateManager = FindObjectOfType<AppStateManager>();
            if (appStateManager == null)
            {
                Debug.LogError("[UserBehaviorSimulator] AppStateManager not found in scene.");
                return false;
            }

            return true;
        }
    }
}