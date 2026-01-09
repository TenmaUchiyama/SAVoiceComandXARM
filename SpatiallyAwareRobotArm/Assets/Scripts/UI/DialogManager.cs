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
        buttonColorImage.color = Color.white;
    }

    private void OnStartListening()
    {
        buttonColorImage.color = Color.green;
    }

    private void OnSpeechRecognized(string arg0)
    {
        userCommand.text = arg0;
        buttonColorImage.color = Color.white;
    }
}
