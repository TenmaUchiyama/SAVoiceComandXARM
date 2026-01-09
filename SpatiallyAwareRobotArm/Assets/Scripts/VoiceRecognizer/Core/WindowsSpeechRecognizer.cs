using UnityEngine.Windows.Speech;
using System; 

namespace SA_XARM.SpeechRecognizer
{public class WindowsSpeechRecognizer : ISpeechRecognizer
{
    public event Action<string> OnRecognized;
    public event Action<string> OnError;

    private DictationRecognizer recognizer;


    

    public void StartListening()
    {

        
        recognizer = new DictationRecognizer();
        recognizer.DictationResult += (text, confidence) =>
        {
            OnRecognized?.Invoke(text);
        };
        recognizer.DictationError += (error, hresult) =>
        {
            OnError?.Invoke(error);
        };
        recognizer.Start();
    }

    public void StopListening()
    {
        recognizer?.Stop();
        recognizer?.Dispose();
    }
}
}