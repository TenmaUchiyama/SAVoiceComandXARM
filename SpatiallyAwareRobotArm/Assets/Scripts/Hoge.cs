using System.Collections;
using System.Collections.Generic;
using System.Threading.Tasks;
using SA_XARM.Network.Request;
using UnityEngine;

public class Hoge : MonoBehaviour
{
    

    public void SendCalibrationWrap()
    {
        _ = SendCalibration();
    }

    public async Task SendCalibration()
    {
        await XarmAppServerQueryRequester.Instance.SendCalibrationRequest();
    }
}
