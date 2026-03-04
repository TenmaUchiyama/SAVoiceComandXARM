using System;
using System.Threading.Tasks;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;
using UnityEngine.Windows.Speech;

namespace SA_XARM.SpeechRecognizer
{
    public class SpeechRecognitionManager : MonoBehaviour
    {

        public bool isListening { get; private set; } = false;
        private bool isTransitioning = false;
        private string recognizedText = "";

        public UnityEvent<string> _onSpeechRecognized;
        public UnityEvent _onStartListening;
        public UnityEvent _onStopListening;
        public UnityEvent _onSilenceTimeout;

        private ISpeechRecognizer speechRecognizer;
        private bool pendingSilenceTimeout = false;



        void Awake()
        {
            // UnityEvent が Inspector 未設定でも落ちないように
            _onSpeechRecognized ??= new UnityEvent<string>();
            _onStartListening ??= new UnityEvent();
            _onStopListening ??= new UnityEvent();
            _onSilenceTimeout ??= new UnityEvent();

            // Speech recognizer 作成
            speechRecognizer = SpeechRecognizerFactory.Create();
            if (speechRecognizer == null)
            {
                SafeLog("[SpeechRecognitionManager] ❌ SpeechRecognizerFactory.Create() returned null. (Platform/Settings issue?)");
                enabled = false;
                return;
            }

            speechRecognizer.OnRecognized += OnSpeechRecognized;
            speechRecognizer.OnError += OnVoiceError;
            speechRecognizer.OnSilenceTimeout += OnSilenceTimeout;

            SafeLog("[SpeechRecognitionManager] Selected Recognizer: " + SpeechRecognizerFactory.selectedRecognizer);
        }

        private void Start()
        {
     

            // ここで一回、参照が刺さってるか確認ログ（null犯人特定の第一歩）
        }

        void Update()
        {
            if (pendingSilenceTimeout)
            {
                pendingSilenceTimeout = false;
                HandleSilenceTimeoutAsync();
            }
        }

        private void OnSilenceTimeout()
        {
            SafeLog("[SpeechRecognitionManager] Silence timeout detected");
            pendingSilenceTimeout = true;
        }

        private async void HandleSilenceTimeoutAsync()
        {
            if (isListening && !isTransitioning)
            {
                SafeLog("[SpeechRecognitionManager] Silence timeout - auto stopping");
                await StopListeningAsync();
                _onSilenceTimeout?.Invoke();
            }
        }

        private void OnVoiceError(string text)
        {
            SafeLog("[SpeechRecognitionManager] Voice Error: " + text);
        }

        private void OnSpeechRecognized(string text)
        {
            SafeLog("[SpeechRecognitionManager] Recognized: " + text);

            recognizedText = text;
            // 認識完了後はボタンを半透明に戻す

            _onSpeechRecognized?.Invoke(text);
        }

        public async void ToggleListening()
        {
            if (isTransitioning)
            {
                SafeLog("[SpeechRecognitionManager] State transition in progress");
                return;
            }

            if (isListening)
            {
                await StopListeningAsync();
            }
            else
            {
                await StartListeningAsync();
            }
        }

        public async void StartListening()
        {
            await StartListeningAsync();
           
        }

        public async void StopListening()
        {
            await StopListeningAsync();
        }

        private async Task StartListeningAsync()
        {
            if (isListening || isTransitioning)
            {
                SafeLog("[SpeechRecognitionManager] Already listening or transitioning");
                return;
            }

            // ここで null なら確実に落ちるので先に弾く
            if (speechRecognizer == null)
            {
                SafeLog("[SpeechRecognitionManager] ❌ speechRecognizer is null. (Awake failed or disabled?)");
                return;
            }

            isTransitioning = true;
            SafeLog("[SpeechRecognitionManager] StartListening");


            try
            {
                // Unity API: main thread only
                var status = PhraseRecognitionSystem.Status;
                SafeLog("[SpeechRecognitionManager] PhraseRecognitionSystem.Status = " + status);

                if (status == SpeechSystemStatus.Running)
                {
                    SafeLog("[SpeechRecognitionManager] Shutdown PhraseRecognitionSystem");
                    PhraseRecognitionSystem.Shutdown();
                }

                SafeLog("[SpeechRecognitionManager] speechRecognizer.StartListening()...");
                speechRecognizer.StartListening(); // ← ここで落ちる可能性が高い

                isListening = true;

                _onStartListening?.Invoke();
            }
            catch (Exception ex)
            {
                // Message だけじゃなく ToString() でスタックトレース出す
                SafeLog("[SpeechRecognitionManager] StartListening failed:\n" + ex.ToString());
            }
            finally
            {
                isTransitioning = false;
            }

            await Task.CompletedTask;
        }

        private async Task StopListeningAsync()
        {
            if (!isListening || isTransitioning)
            {
                SafeLog("[SpeechRecognitionManager] Not listening or transitioning");
                return;
            }

            if (speechRecognizer == null)
            {
                SafeLog("[SpeechRecognitionManager] ❌ speechRecognizer is null.");
                return;
            }

            isTransitioning = true;
            SafeLog("[SpeechRecognitionManager] StopListening");


            try
            {
                SafeLog("[SpeechRecognitionManager] speechRecognizer.StopListening()...");
                speechRecognizer.StopListening();

                var status = PhraseRecognitionSystem.Status;
                SafeLog("[SpeechRecognitionManager] PhraseRecognitionSystem.Status = " + status);

                if (status == SpeechSystemStatus.Stopped)
                {
                    SafeLog("[SpeechRecognitionManager] Restart PhraseRecognitionSystem");
                    PhraseRecognitionSystem.Restart();
                }

                isListening = false;

                _onStopListening?.Invoke();
            }
            catch (Exception ex)
            {
                SafeLog("[SpeechRecognitionManager] StopListening failed:\n" + ex.ToString());
            }
            finally
            {
                isTransitioning = false;
            }

            await Task.CompletedTask;
        }

   

        // SpatialDebugLog が null でも落ちないようにする
        private void SafeLog(string msg)
        {
            if (SpatialDebugLog.Instance != null)
                SpatialDebugLog.Instance.Log(msg);
            else
                Debug.Log(msg);
        }




        public string GetRecognizedText()
        {
            return recognizedText;
        }   
    }
}
