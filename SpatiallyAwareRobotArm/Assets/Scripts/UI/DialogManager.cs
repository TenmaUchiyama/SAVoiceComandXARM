using System;
using System.Collections;
using System.Collections.Generic;
using MixedReality.Toolkit.UX;
using SA_XARM.SpeechRecognizer;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class DialogManager : MonoBehaviour
{
    [SerializeField] private SpeechRecognitionManager speechRecognitionManager;

    [SerializeField] private TextMeshProUGUI userCommand; 

    [SerializeField] private RawImage buttonColorImage;

    [SerializeField] private PressableButton recordingButton;

  

    void Start()
    {
        speechRecognitionManager._onSpeechRecognized.AddListener(OnSpeechRecognized);
        speechRecognitionManager._onStartListening.AddListener(OnStartListening);
        speechRecognitionManager._onStopListening.AddListener(OnStopListening);

        recordingButton.OnClicked.AddListener(() =>
        {
            if(speechRecognitionManager.isListening)
            {
                speechRecognitionManager.StopListening();
            }
            else
            {
                speechRecognitionManager.StartListening();
            }
        });
    }

    private void OnStopListening()
    {
        // 半透明に戻す
        Color semiTransparent = Color.white;
        semiTransparent.a = 0.5f;
        buttonColorImage.color = semiTransparent;
    }

    private void OnStartListening()
    {
        // 完全に不透明にする
        Color fullOpaque = Color.green;
        fullOpaque.a = 1.0f;
        buttonColorImage.color = fullOpaque;
    }

    private void OnSpeechRecognized(string arg0)
    {
        userCommand.text = arg0;
        // 認識完了後は半透明に戻す
        Color semiTransparent = Color.white;
        semiTransparent.a = 0.5f;
        buttonColorImage.color = semiTransparent;
    }
}
