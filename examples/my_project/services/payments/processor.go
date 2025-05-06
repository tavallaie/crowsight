// my_project/services/payments/processor.go
package payments

import (
    "encoding/json"
    "fmt"
    "net/http"
)

type PaymentRequest struct {
    OrderID string  `json:"order_id"`
    Amount  float64 `json:"amount"`
}

type PaymentResponse struct {
    Status  string `json:"status"`
    Message string `json:"message"`
}

func Processor(w http.ResponseWriter, r *http.Request) {
    var req PaymentRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "Invalid request", http.StatusBadRequest)
        return
    }
    // simulate processing
    fmt.Printf("Processing payment for order %s: $%.2f\n", req.OrderID, req.Amount)
    resp := PaymentResponse{Status: "success", Message: "Payment processed"}
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}
