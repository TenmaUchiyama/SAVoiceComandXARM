using System;



namespace SA_XARM.SpeechRecognizer
{
   using System;

public interface ISpeechRecognizer
{

    event Action<string> OnRecognized;

  
    event Action<string> OnError;

    /// <summary>
    /// 無音タイムアウトで認識が終了した時に発火
    /// </summary>
    event Action OnSilenceTimeout;

    void StartListening();

    void StopListening();
}

}