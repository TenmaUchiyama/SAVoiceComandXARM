using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using SA_XARM.Network.Websocket;
using TMPro;

namespace SA_XARM.Calibration
{
public class CalibratorRestrerSwitcher : MonoBehaviour
{
   [SerializeField] GameObject calibratorObject;
   [SerializeField] GameObject restrerObject;
   [SerializeField] GameObject gridParent;

   [SerializeField] TextMeshProUGUI currentModeText;



    void Start()
    {
        SpatialDebugLog.Instance.Log("[CalibratorRestrerSwitcher] Initializing...", true);
        currentModeText.text = "Calibrator";
        WebSocketManager.Instance.On<MouseKeyInput>("KeyInput", (input) => 
        {
            if (input.key == "e" || input.key == "E")
            {
                SpatialDebugLog.Instance.Log("℮ Remote E Key Received! Clearing Grid Objects.", true, "red"); 
              foreach(GameObject obj in gridParent.GetComponentsInChildren<GameObject>())
              {
                  Destroy(obj);
              }
            }
        }); 
    
        WebSocketManager.Instance.On<MouseKeyInput>("KeyInput", (input) => 
        {
            if (input.key == "c" || input.key == "C")
            {
                SpatialDebugLog.Instance.Log("© Remote C Key Received! Switching to Calibrator.", true, "red");
                 foreach(GameObject obj in gridParent.GetComponentsInChildren<GameObject>())
              {
                  Destroy(obj);
              }
                calibratorObject.SetActive(true);
                restrerObject.SetActive(false);
                currentModeText.text = "Current Mode: Calibrator";
            }
            else if (input.key == "r" || input.key == "R")
            {
                SpatialDebugLog.Instance.Log("® Remote R Key Received! Switching to Restorer.", true, "red");
                 foreach(GameObject obj in gridParent.GetComponentsInChildren<GameObject>())
              {
                  Destroy(obj);
              }
                calibratorObject.SetActive(false);
                restrerObject.SetActive(true);
                currentModeText.text = "Current Mode: Restore";
            }
        });
    }
}
}