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
        SpatialDebugLog.Instance?.Log("[CalibratorRestrerSwitcher] Initializing...", true);
        currentModeText.text = "Calibrator";

        if (WebSocketManager.Instance == null)
        {
            SpatialDebugLog.Instance?.Log("[CalibratorRestrerSwitcher] WebSocketManager.Instance is NULL", true, "yellow");
            return;
        }

        WebSocketManager.Instance.On<MouseKeyInput>("KeyInput", (input) =>
        {
            if (input.key == "e" || input.key == "E")
            {
                SpatialDebugLog.Instance?.Log("℮ Remote E Key Received! Clearing Grid Objects.", true, "red");
                DestroyAllChildren(gridParent);
            }
        });

        WebSocketManager.Instance.On<MouseKeyInput>("KeyInput", (input) =>
        {
            if (input.key == "c" || input.key == "C")
            {
                SpatialDebugLog.Instance?.Log("© Remote C Key Received! Switching to Calibrator.", true, "red");
                DestroyAllChildren(gridParent);
                calibratorObject.SetActive(true);
                restrerObject.SetActive(false);
                currentModeText.text = "Current Mode: Calibrator";
            }
            else if (input.key == "r" || input.key == "R")
            {
                SpatialDebugLog.Instance?.Log("® Remote R Key Received! Switching to Restorer.", true, "red");
                DestroyAllChildren(gridParent);
                calibratorObject.SetActive(false);
                restrerObject.SetActive(true);
                currentModeText.text = "Current Mode: Restore";
            }
        });
    }

    /// <summary>
    /// 子オブジェクトだけを安全に破棄する（親は残す）。
    /// リストに収集してから Destroy するため、foreach 中のコレクション変更リスクを回避。
    /// </summary>
    private static void DestroyAllChildren(GameObject parent)
    {
        if (parent == null) return;

        var children = new List<GameObject>();
        foreach (Transform child in parent.transform)
        {
            children.Add(child.gameObject);
        }
        for (int i = 0; i < children.Count; i++)
        {
            Destroy(children[i]);
        }
    }
}
}
