// sseUtils.js
export class ResilientSSE {
  constructor(url, options = {}) {
    this.url = url;
    this.options = options;
    this.maxReconnect = options.maxReconnect || 5;
    this.baseDelay = options.baseDelay || 1000;
    
    this.reconnectAttempts = 0;
    this.es = null;
    this.isConnected = false;
  }

  connect(onMessage, onError) {
    if (this.es) {
      this.es.close();
    }

    console.log(`[SSE] Connecting to ${this.url}...`);
    this.es = new EventSource(this.url, this.options);
    this.isConnected = true;

    this.es.onopen = () => {
      console.log("[SSE] Connection established.");
      this.reconnectAttempts = 0; // Reset retries on successful connection
    };

    this.es.onmessage = (event) => {
      if (onMessage) onMessage(event.data);
    };

    this.es.onerror = (error) => {
      console.warn("[SSE] Connection error. Operation aborted or dropped.", error);
      this.es.close();
      this.isConnected = false;
      
      if (onError) onError(error);
      
      this.handleReconnect(onMessage, onError);
    };
  }

  handleReconnect(onMessage, onError) {
    if (this.reconnectAttempts < this.maxReconnect) {
      // Exponential backoff: 1s, 2s, 4s, 8s...
      const delay = this.baseDelay * Math.pow(2, this.reconnectAttempts);
      console.log(`[SSE] Reconnecting in ${delay}ms (Attempt ${this.reconnectAttempts + 1}/${this.maxReconnect})`);
      
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect(onMessage, onError);
      }, delay);
    } else {
      console.error("[SSE] Max retries reached. Connection permanently failed.");
    }
  }

  disconnect() {
    if (this.es) {
      console.log("[SSE] Connection manually closed.");
      this.es.close();
      this.es = null;
    }
    this.isConnected = false;
  }
}
