using System.Collections;
using System.Collections.Generic;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;




namespace SA_XARM.Network.Request
{
public class QueryRequester : MonoBehaviour
{


    [SerializeField] private string hostAddress = "localhost";
    [SerializeField] private int portNum = 8080;
       

      public async Task<string> GetRequest(string path)
        {
            string safePath = (path ?? string.Empty).TrimStart('/');
            string url = $"http://{hostAddress}:{portNum}/{safePath}";    
            Debug.Log($"[ActionServerConnector] Sending GET request to {url}");        
        using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                var operation = request.SendWebRequest();

                while (!operation.isDone)
                {
                    await Task.Yield();
                }

                string result = HandleResponse(request);
                return result;
            }
        }
    



    public async Task<string> PostRequest(string path, string jsonBody)
        {
            string safePath = (path ?? string.Empty).TrimStart('/');
            string url = $"http://{hostAddress}:{portNum}/{safePath}";
            
            Debug.Log($"[QueryRequester] POST to {url}");
            Debug.Log($"[QueryRequester] Request Body: {jsonBody}");

            using (UnityWebRequest request = new UnityWebRequest(url, "POST"))
            {
                byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonBody);
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();


                request.SetRequestHeader("Content-Type", "application/json");

                var operation = request.SendWebRequest();

                while (!operation.isDone)
                {
                    await Task.Yield();
                }

                string result = HandleResponse(request);
                return result;
              
            }
        }

    private string HandleResponse(UnityWebRequest request)
{
    if (request.result != UnityWebRequest.Result.Success)
    {
        // エラー時もレスポンスボディを取得して詳細を表示
        string errorBody = "";
        if (request.downloadHandler != null && request.downloadHandler.data != null)
        {
            errorBody = Encoding.UTF8.GetString(request.downloadHandler.data);
        }
        
        Debug.LogError($"Error: {request.error} (Response Code: {request.responseCode})");
        if (!string.IsNullOrEmpty(errorBody))
        {
            Debug.LogError($"Error Response Body: {errorBody}");
        }
        return null; 
    }
    else
    {
        // downloadHandlerやdataがnullでないことを確認してから取得
        if (request.downloadHandler != null && request.downloadHandler.data != null)
        {
            string result = Encoding.UTF8.GetString(request.downloadHandler.data);


            if (string.IsNullOrEmpty(result) || result == "null")
            {
                Debug.LogWarning("Server returned null or empty response.");
                return null; 
            }


            return result; // 成功時にレスポンスボディを返す
        }
        else
        {
            Debug.LogWarning("No response data received from the server.");
            return ""; // またはnullや特定のメッセージなどを返す
        }
    }
}


}
}