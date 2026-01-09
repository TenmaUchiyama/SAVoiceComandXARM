using System.Collections;
using System.Collections.Generic;
using UnityEngine;





namespace SA_XARM.Network.Server{
public class AppServer :  HttpServer
{
    
    [SerializeField] private string host = "0.0.0.0";
    [SerializeField] private int port = 7070;


    void Start() {
        Debug.Log("[App Server] Server Initializing."); 
        InitServer(host, port);

        Get("/", async (context) =>
        {
            Debug.Log("[App Server] GET / received");
            await context.Respond(200, "Hello from Hololens App Server!");
        });

    }
}
}