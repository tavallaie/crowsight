// my_project/services/notifications.go
package main

import (
    "fmt"
    "net/http"
)

func NotifyHandler(w http.ResponseWriter, r *http.Request) {
    // TODO: handle webhook retries
    fmt.Fprintln(w, "Notification received")
}

func main() {
    http.HandleFunc("/notify", NotifyHandler)
    fmt.Println("Notification service running on :8081")
    http.ListenAndServe(":8081", nil)
}
