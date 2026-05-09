// sseUtils.js
export class ResilientSSE {
  constructor(url, options = {}) {
    this.url = url;
    this.options = options;
    this.maxReconnect = options.maxReconnect || 10;
    this.baseDelay = options.baseDelay || 1000;
    
    this.reconnectAttempts = 0;
    this.es = null;
    this.isConnected = false;
    this.manualClose = false;
  }

  connect(onMessage, onError) {
    if (this.es) {
      this.es.close();
    }

    this.manualClose = false;
    console.log(`[SSE] Connecting to ${this.url}...`);
    
    try {
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
        // If manually closed, don't attempt to reconnect
        if (this.manualClose) return;

        // Specifically handle DOMException: Aborted
        // Some browsers/environments throw DOMException when the connection is aborted
        if (
          error instanceof DOMException && 
          (error.name === 'AbortError' || error.message.includes('Aborted'))
        ) {
          console.warn("[SSE] Connection aborted by browser (DOMException: Aborted). Reconnecting gracefully.");
        } else {
          console.warn("[SSE] Connection error.", error);
        }
        
        // Close the current instance
        if (this.es) {
          this.es.close();
          this.es = null;
        }
        this.isConnected = false;
        
        if (onError) onError(error);
        
        // Handle reconnection
        this.handleReconnect(onMessage, onError);
      };
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
         console.warn("[SSE] Initialization aborted (DOMException: Aborted).", err);
      } else {
         console.error("[SSE] Failed to initialize EventSource:", err);
      }
      this.handleReconnect(onMessage, onError);
    }
  }

  handleReconnect(onMessage, onError) {
    if (this.manualClose) return;

    if (this.reconnectAttempts < this.maxReconnect) {
      // Exponential backoff with jitter: (2^n * 1000) + random
      const delay = (this.baseDelay * Math.pow(2, this.reconnectAttempts)) + (Math.random() * 1000);
      console.log(`[SSE] Reconnecting in ${Math.round(delay)}ms (Attempt ${this.reconnectAttempts + 1}/${this.maxReconnect})`);
      
      setTimeout(() => {
        if (this.manualClose) return;
        this.reconnectAttempts++;
        this.connect(onMessage, onError);
      }, delay);
    } else {
      console.error("[SSE] Max retries reached. Connection permanently failed.");
    }
  }

  disconnect() {
    this.manualClose = true;
    if (this.es) {
      console.log("[SSE] Connection manually closed.");
      this.es.close();
      this.es = null;
    }
    this.isConnected = false;
  }
}
