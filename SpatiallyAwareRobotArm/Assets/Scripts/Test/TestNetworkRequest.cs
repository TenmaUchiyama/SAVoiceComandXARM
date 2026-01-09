using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using SA_XARM.Network.Request;
using Newtonsoft.Json;
using TMPro;


public class TestNetworkRequest : QueryRequester
{
  
     

    [SerializeField] private string host = "192.168.108.164";
    [SerializeField] private int port = 8800;
    [SerializeField] private bool speechRequired = true;
    [SerializeField] private string debugText = "";
    [SerializeField] private TextMeshProUGUI responseText;


    

    public async void SendHelloRequest()
    {
        string path = "hello";
        string jsonData = "{}";
        string url = $"http://{host}:{port}";
        Debug.Log($"[TestNetworkRequest]<color=yellow>Sending Test Query to {path}: {jsonData}</color>");

        string response = await GetRequest(url);
        Debug.Log($"[TestNetworkRequest] Get response: {response}");
        responseText.text = response;
    }


    public async void TestPostRequest()
    {
        string url = $"http://{host}:{port}/post-test";
        var sendingObj = new { msg = "Hello from Hololens TestNetworkRequest" };
        string jsonData = JsonConvert.SerializeObject(sendingObj);

        Debug.Log($"[TestNetworkRequest]<color=yellow>Sending Test POST to {url}: {jsonData}</color>");

        string response = await PostRequest(url, jsonData);
        Debug.Log($"[TestNetworkRequest] Pose Response {response}");
        responseText.text = response;

    }



}
