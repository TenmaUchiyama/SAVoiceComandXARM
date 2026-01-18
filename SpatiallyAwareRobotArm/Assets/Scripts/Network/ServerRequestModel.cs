using System; 

namespace SA_XARM.Network.Request
{
    

    [Serializable]
    public record GridPickRequest
    {
        public int x;
        public int y;
        public GridPickRequest(int x, int y)
        {
            this.x = x;
            this.y = y;
        }
    }
}