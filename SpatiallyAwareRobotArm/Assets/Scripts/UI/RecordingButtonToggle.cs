using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class RecordingButtonToggle : MonoBehaviour
{
    private bool isRecording = false;


    public void ToggleRecording()
    {
        isRecording = !isRecording;

        if (isRecording)
        {
            Debug.Log("[RecordingButtonToggle] Recording Started");
            // 録音開始の処理をここに追加
        }
        else
        {
            Debug.Log("[RecordingButtonToggle] Recording Stopped");
            // 録音停止の処理をここに追加
        }
    }
}
