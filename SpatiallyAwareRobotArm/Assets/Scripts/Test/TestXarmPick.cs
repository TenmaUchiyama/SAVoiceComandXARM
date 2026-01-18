using System.Collections;
using System.Collections.Generic;
using SA_XARM.Network.Request;
using UnityEngine;

public class TestXarmPick : MonoBehaviour
{
    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        if(Input.GetKeyDown(KeyCode.P))
        {
            if(XarmAppServerQueryRequester.Instance != null)
            {
                _ = XarmAppServerQueryRequester.Instance.SendPickGridRequest(1, 2);
            }
            else
            {
                Debug.LogError("<color=red>[TestXarmPick] XarmAppServerQueryRequesterのインスタンスが見つかりません。</color>");
            }
        }
    }
}
