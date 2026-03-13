using System;



namespace SA_XARM.SpeechRecognizer
{
   using System;

public interface ISpeechRecognizer
{
    event Action<string> OnRecognized;
    event Action<string> OnError;
    event Action OnCompleted; // 認識セッションが終了したとき（タイムアウト等）

    void StartListening();
    void StopListening();
}

}