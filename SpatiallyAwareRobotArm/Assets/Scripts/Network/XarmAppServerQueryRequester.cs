using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Events;






namespace SA_XARM.Network.Request
{
    
    public class XarmAppServerQueryRequester : QueryRequester
{


    public static XarmAppServerQueryRequester Instance { get; private set; }

    
    [SerializeField] private bool speechRequired = true;
    [SerializeField] private string debugText = "";



        public UnityEvent<string> OnReceiveResponseFromLLM;
        private bool _isRequesting = false;
        public bool IsRequesting => _isRequesting;


            private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
        }
    }


        public async Task<string> SendQuery(string path, string jsonData)
    {
        _isRequesting = true;
        string safePath = (path ?? string.Empty).TrimStart('/');
      
        if (SpatialDebugLog.Instance != null)
        {
            SpatialDebugLog.Instance.Log($"<color=yellow>Sending Query to {safePath}: {jsonData}</color>", debugText != "");
        }

        try
        {
            string response = await PostRequest(safePath, jsonData);
            return response;
        }
        catch (Exception ex)
            {
                if (SpatialDebugLog.Instance != null)
                {
                    SpatialDebugLog.Instance.Log($"<color=red>[XarmAppServerQueryRequester] Error sending query: {ex.Message}</color>", debugText != "");
                }
                return string.Empty;
            }
        finally
        {
            _isRequesting = false;
        }
    }



    public async Task<string> SendPickGridRequest(int x_grid, int y_grid)
    {
        var requestPayload = new GridPickRequest(x_grid, y_grid);
        string jsonBody = JsonConvert.SerializeObject(requestPayload, Formatting.None);
        if (SpatialDebugLog.Instance != null)
        {
            SpatialDebugLog.Instance.Log($"[XarmAppServerQueryRequester] Sending GridPickRequest: {jsonBody}", debugText != "");
        }
        string response = await PostRequest("xarm_pick", jsonBody);
        if (SpatialDebugLog.Instance != null)
        {
            SpatialDebugLog.Instance.Log($"[XarmAppServerQueryRequester] Received Response: {response}", debugText != "");
        }
        return response;
    }

        public async Task SendCalibrationRequest()
        {
            await GetRequest("calibration");
            if (SpatialDebugLog.Instance != null)
            {
                SpatialDebugLog.Instance.Log("<color=white>[XarmAppServerQueryRequester] Calibration request sent.</color>", debugText != "");
            }
        }
    }
}