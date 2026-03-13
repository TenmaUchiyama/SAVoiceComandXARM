using UnityEngine.Windows.Speech;
using UnityEngine;
using System;

namespace SA_XARM.SpeechRecognizer
{
    public class WindowsSpeechRecognizer : ISpeechRecognizer
    {
        public event Action<string> OnRecognized;
        public event Action<string> OnError;
        public event Action OnCompleted;

        private DictationRecognizer recognizer;
        private bool _shouldBeListening = false;

        private void Log(string msg)
        {
            SpatialDebugLog.Instance?.Log(msg);
        }

        public void StartListening()
        {
            Log("[WinSR] StartListening called");

            try
            {
                _shouldBeListening = true;

                // 既存のrecognizerがあれば安全に破棄
                if (recognizer != null)
                {
                    Log("[WinSR] Disposing old recognizer...");
                    try
                    {
                        if (recognizer.Status == SpeechSystemStatus.Running)
                        {
                            recognizer.Stop();
                        }
                        recognizer.Dispose();
                    }
                    catch (Exception ex)
                    {
                        Log("[WinSR] Dispose error: " + ex.Message);
                    }
                    recognizer = null;
                }

                Log($"[WinSR] PhraseRecognitionSystem.Status at Start: {PhraseRecognitionSystem.Status}");
                Log("[WinSR] Creating new DictationRecognizer...");
                recognizer = new DictationRecognizer();
                Log("[WinSR] DictationRecognizer created OK");

                recognizer.InitialSilenceTimeoutSeconds = 0f;
                recognizer.AutoSilenceTimeoutSeconds = 0f;
                Log("[WinSR] Timeouts set to 0");

                recognizer.DictationResult += (text, confidence) =>
                {
                    Log($"[WinSR] Result: \"{text}\" (confidence: {confidence})");
                    try { OnRecognized?.Invoke(text); }
                    catch (Exception ex) { Log("[WinSR] OnRecognized handler error: " + ex.Message); }
                };

                recognizer.DictationHypothesis += (text) =>
                {
                    Log($"[WinSR] Hypothesis: \"{text}\"");
                };

                recognizer.DictationError += (error, hresult) =>
                {
                    Log($"[WinSR] ERROR: {error} (hresult: {hresult})");
                    try { OnError?.Invoke(error); }
                    catch (Exception ex) { Log("[WinSR] OnError handler error: " + ex.Message); }
                };

                recognizer.DictationComplete += (cause) =>
                {
                    Log($"[WinSR] Complete. Cause: {cause}");
                    if (_shouldBeListening)
                    {
                        try { OnCompleted?.Invoke(); }
                        catch (Exception ex) { Log("[WinSR] OnCompleted handler error: " + ex.Message); }
                    }
                };

                Log("[WinSR] Calling recognizer.Start()...");
                recognizer.Start();
                Log($"[WinSR] recognizer.Start() done. Status: {recognizer.Status}");
            }
            catch (Exception ex)
            {
                Log($"[WinSR] FATAL in StartListening: {ex.GetType().Name}: {ex.Message}");
                Log($"[WinSR] StackTrace: {ex.StackTrace}");
            }
        }

        public void StopListening()
        {
            Log("[WinSR] StopListening called");
            _shouldBeListening = false;
            try
            {
                if (recognizer != null)
                {
                    if (recognizer.Status == SpeechSystemStatus.Running)
                    {
                        recognizer.Stop();
                    }
                    recognizer.Dispose();
                    recognizer = null;
                }
            }
            catch (Exception ex)
            {
                Log($"[WinSR] StopListening error: {ex.Message}");
            }
        }
    }
}
