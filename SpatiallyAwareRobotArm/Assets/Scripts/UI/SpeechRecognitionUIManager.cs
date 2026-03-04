using System.Collections;
using System.Collections.Generic;
using System.Threading.Tasks;
using MixedReality.Toolkit.UX;
using SA_XARM.Network.Request;
using SA_XARM.SpeechRecognizer;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class SpeechRecognitionUIManager : MonoBehaviour
{


    [SerializeField] private SpeechRecognitionManager speechRecognitionManager;
    [SerializeField] private CommandClient commandClient;
    [SerializeField] private GameObject dialogUI;
    [SerializeField] private GameObject voiceRecognionUI; 
    [SerializeField] private GameObject recordingIcon;
    [SerializeField] private TextMeshProUGUI recordedText; 
    [SerializeField] private GameObject sendButton;

    [Header("Audio")]
    
     private AudioSource audioSource;
    [SerializeField] private AudioClip onSound;
    [SerializeField] private AudioClip offSound;


    // Start is called before the first frame update
    void Start()
    {

        


        if(speechRecognitionManager == null) return;
        audioSource = GetComponent<AudioSource>();
        speechRecognitionManager._onStartListening.AddListener(() =>
        {
            dialogUI.SetActive(true);
            SetRecordedText("Listening...");
            ToggleRecordingIconVisibility(true);
            PlaySound(onSound);
        });

        speechRecognitionManager._onStopListening.AddListener(() =>
        {
           
            ToggleRecordingIconVisibility(false);
            PlaySound(offSound);
        });


        speechRecognitionManager._onSpeechRecognized.AddListener((text) =>
        {
            SetRecordedText(text);
            ToggleRecordingIconVisibility(false);
            sendButton.SetActive(true);
        });
    }


    public void SendUtteredCommand()
    {
        if (commandClient != null && recordedText != null)
        {
            string text = speechRecognitionManager.GetRecognizedText();
            commandClient.SendCommand(text);
            SetRecordedText("Command sent: " + text);
            sendButton.SetActive(false);
        }
    }



    public void ToggleToWake()
    {
        Debug.Log("Toggle to Wake UI");
    }


    public void ToggleToSpeech()
    {
        Debug.Log("Toggle to Speech UI");
    }



    


 
    public void SendCalibration()
    {
        _ =  XarmAppServerQueryRequester.Instance.SendCalibrationRequest();
    }



    public void SetRecordedText(string text)
    {
        if (recordedText != null)
        {
            recordedText.text = text;
        }
    }   


    public void ToggleRecordingIconVisibility(bool isVisible)
    {
        recordingIcon.SetActive(isVisible);
    }

    private void PlaySound(AudioClip clip)
    {
        if (audioSource != null && clip != null)
        {
            audioSource.PlayOneShot(clip);
        }
    }
    
}
