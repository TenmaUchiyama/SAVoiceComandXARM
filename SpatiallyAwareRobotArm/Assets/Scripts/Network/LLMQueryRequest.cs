using System.Collections;
using System.Collections.Generic;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Events;






namespace SA_XARM.Network.Request
{
    
    public class LLMQueryRequest : QueryRequester
{
    [SerializeField] private string host = "localhost";
    [SerializeField] private int port = 8800;
    [SerializeField] private bool speechRequired = true;
    [SerializeField] private string debugText = "";



        public UnityEvent<string> OnReceiveResponseFromLLM;
        private bool _isRequesting = false;
        public bool IsRequesting => _isRequesting;

  public async Task SendQuery(string path, string jsonData)
    {
        string url = $"http://{host}:{port}/{path}";
        Debug.Log($"<color=yellow>Sending Query to {path}: {jsonData}</color>");

        await PostRequest(url, jsonData);

        _isRequesting = false;
    }





}
}