using System;
using UnityEngine;

namespace SA_XARM.SpeechRecognizer
{
    public class PlayModeMicrophoneSpeechRecognizer : ISpeechRecognizer
    {
        public event Action<string> OnRecognized;
        public event Action<string> OnError;

        [Header("Debug Settings")]
        [SerializeField] private int sampleRate = 16000;
        [SerializeField] private int recordLengthSec = 10;
        [SerializeField] private bool autoSelectFirstMic = true;

        private AudioClip clip;
        private string selectedMic;

        public void StartListening()
        {
            Debug.Log("[PlayModeMic] StartListening");

            if (Microphone.devices.Length == 0)
            {
                Debug.LogError("[PlayModeMic] No microphone devices found");
                OnError?.Invoke("No microphone devices");
                return;
            }

            // 使用マイク一覧を出力
            Debug.Log("[PlayModeMic] Available microphones:");
            foreach (var device in Microphone.devices)
            {
                Debug.Log(" - " + device);
            }

            // マイク選択（デバッグ優先）
            selectedMic = autoSelectFirstMic
                ? Microphone.devices[0]
                : null;

            Debug.Log($"[PlayModeMic] Selected mic: {selectedMic}");

            try
            {
                clip = Microphone.Start(
                    selectedMic,
                    false,
                    recordLengthSec,
                    sampleRate
                );
            }
            catch (Exception e)
            {
                Debug.LogError("[PlayModeMic] Microphone.Start failed: " + e);
                OnError?.Invoke(e.Message);
                return;
            }

            Debug.Log("[PlayModeMic] Recording started");
        }

        public void StopListening()
        {
            Debug.Log("[PlayModeMic] StopListening");

            if (clip == null)
            {
                Debug.LogWarning("[PlayModeMic] StopListening called but clip is null");
                OnError?.Invoke("Clip is null");
                return;
            }

            Microphone.End(selectedMic);

            int position = Microphone.GetPosition(selectedMic);
            Debug.Log($"[PlayModeMic] Recorded samples: {position}");

            // 波形データ取得（最初の数サンプルだけ表示）
            float[] samples = new float[Mathf.Min(position, 32)];
            clip.GetData(samples, 0);

            string preview = "";
            for (int i = 0; i < samples.Length; i++)
            {
                preview += samples[i].ToString("F3") + ", ";
            }

            Debug.Log("[PlayModeMic] Sample preview: " + preview);

            // 簡易音量チェック
            float max = 0f;
            foreach (var s in samples)
            {
                max = Mathf.Max(max, Mathf.Abs(s));
            }

            Debug.Log($"[PlayModeMic] Max amplitude (preview): {max:F3}");

            // PlayMode用の疑似結果通知
            OnRecognized?.Invoke("[PLAYMODE_AUDIO_READY]");
        }
    }
}
