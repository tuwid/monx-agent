package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"time"
)

func main() {
	args := os.Args[1:]
	if len(args) == 0 {
		fmt.Println("Usage: agent [apiKey]")
		return
	}
	apiKEY := args[0]
	apiURI := strings.Join([]string{"https://demo9829362.mockable.io/api?apiKey=", apiKEY}, "")
	ticker := time.NewTicker(2 * time.Second)
	for {
		<-ticker.C
		go interval(apiURI)
	}
}

// Representing a json response
type JSONResponse struct {
	Commands []string `json:"commands"`
}

func interval(apiURI string) {
	// commands http request
	resp, err := http.Get(apiURI) // https://monx.me/
	if err != nil {
		fmt.Println(err) // TODO: on step 2: log errors
		return
	}
	defer resp.Body.Close()
	// get response
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		fmt.Println(err) // TODO: on step 2: log errors
		return
	} else if body == nil {
		fmt.Println("Wrong body response.") // TODO: on step 2: log errors
		return
	}
	// json decode
	var jsonObject JSONResponse
	err = json.Unmarshal(body, &jsonObject)
	if err != nil {
		fmt.Println(err)
	}
	var commands = jsonObject.Commands
	if len(commands) == 0 {
		return // there are no commands
	}
	for _, command := range commands {
		// out, err := exec.Command("cmd", "/C", command).Output() // windows
		out, err := exec.Command("bash", "-c", command).Output() // unix
		if err != nil {
			fmt.Println(err)
		}
		fmt.Println(string(out))
	}
}
