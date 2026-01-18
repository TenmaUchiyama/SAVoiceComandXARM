using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class InteractionTest : MonoBehaviour
{
    // Start is called before the first frame update
    private Material matRenderer;
    void Start()
    {
        matRenderer = GetComponent<Renderer>().material;
    }

    // Update is called once per frame
    void Update()
    {
        
    }

    public void GazeHover()
    {
        Debug.Log($"<color=green>[InteractionTest] Hoverされましたよ</color>" );
        this.matRenderer.color = Color.green;
    }


    public void GazeUnhover()
    {
        Debug.Log($"<color=blue>[InteractionTest] Unhoverされましやよ</color>" );
        this.matRenderer.color = Color.white;
    }



     public void GazePinch()
    {
        Debug.Log($"<color=red>[InteractionTest] PinchHoverされましたよ</color>" );
        this.matRenderer.color = Color.red;
    }


    public void GazeUnpinch()
    {
        Debug.Log($"<color=cyan>[InteractionTest] UnpinchHoverされましたよ</color>" );
        this.matRenderer.color = Color.cyan;
    }
}
