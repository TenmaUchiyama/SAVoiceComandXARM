using System;



namespace SA_XARM.SpeechRecognizer
{
   using System;

public interface ISpeechRecognizer
{

    event Action<string> OnRecognized;

  
    event Action<string> OnError;


    void StartListening();

    void StopListening();
}

}