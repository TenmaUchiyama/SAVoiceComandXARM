using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Grid : MonoBehaviour
{
   [SerializeField] private int x_grid = 0;
   [SerializeField] private int y_grid = 0;

    [SerializeField] private GameObject gridVisual;
    
    private Material matRenderer;
    void Start()
    {
        matRenderer = gridVisual.GetComponent<Renderer>().material;
    }

    // Update is called once per frame
    void Update()
    {
        
    }



    public void SetGridPosition(int x, int y)
    {
        this.x_grid = x;
        this.y_grid = y;
    }

    public void GazeHover()
    {
        // Debug.Log($"<color=green>[InteractionTest] Hoverされましたよ</color>" );
        this.matRenderer.color = Color.green;
    }


    public void GazeUnhover()
    {
        // Debug.Log($"<color=blue>[InteractionTest] Unhoverされましやよ</color>" );
        this.matRenderer.color = Color.white;
    }



     public void GazePinch()
    {
        // Debug.Log($"<color=red>[InteractionTest] PinchHoverされましたよ</color>" );
        this.matRenderer.color = Color.red;
    }


    public void GazeUnpinch()
    {
        // Debug.Log($"<color=cyan>[InteractionTest] UnpinchHoverされましたよ</color>" );
        this.matRenderer.color = Color.cyan;
    }


    public (int, int) GetGridPosition()
    {
        return (this.x_grid, this.y_grid);
    }
}
