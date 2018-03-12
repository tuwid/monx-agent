package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
)

// TODO:
// - Add system logging support
// - Get command exit code
// - Post output to API
// - Add debug env variable flag

type JSONResponse struct {
	Commands []string `json:"commands"`
}

type agent struct {
	mac      string
	apikey   string
	apiuri   string
	execpath string
	debug    bool
	os       string
	command
}
type command struct {
	execstring  string
	exitcode    int
	interpreter string
	output      string
}

func orFail(err error, msg string) {
	if err != nil {
		log.Fatalf("%s: %s", msg, err)
		panic(fmt.Sprintf("%s: %s", msg, err))
	}
}

func vmDebug(debug bool, msg string) {
	if debug {
		fmt.Println(msg)
	}
}
func (pvm *agent) print() {
	fmt.Println("Agent MAC: ", pvm.mac)
	fmt.Println("Agent KEY: ", pvm.apikey)
	fmt.Println("Agent URI: ", pvm.apiuri)
	fmt.Println("Agent OS: ", pvm.os)
	fmt.Println("Agent PATH: ", pvm.execpath)
}

func (pvm *agent) setMacAddr() {
	interfaces, err := net.Interfaces()
	addr := "aa:bb:cc:dd:ee:ff"
	if err == nil {
		for _, i := range interfaces {
			if i.Flags&net.FlagUp != 0 && bytes.Compare(i.HardwareAddr, nil) != 0 {
				addr = i.HardwareAddr.String()
				break
			}
		}
	}
	r := strings.NewReplacer(":", "-")
	pvm.mac = r.Replace(addr)
}

func (pvm *agent) setEnv(key string) {
	pvm.os = runtime.GOOS
	if os.Getenv("AGENT_DEBUG") == "1" {
		fmt.Println("Turning ON debug logs")
		pvm.debug = true
	}
	pvm.apikey = key
	pvm.apiuri = "https://api.monx.me/api/hub/agent/command?apikey=" + pvm.apikey + "&mac=" + pvm.mac
	if pvm.os == "windows" {
		pvm.execpath = filepath.Join(os.Getenv("TEMP"), "_monxagent.bat")
	} else {
		pvm.execpath = filepath.Join(os.Getenv("HOME"), "_monxagent.sh")
	}
}

func (pvm *agent) getDataFromBase() {
	resp, err := http.Get(pvm.apiuri)

	vmDebug(pvm.debug, "Got code "+strconv.Itoa(resp.StatusCode)+" from API")
	orFail(err, "Error while GETing from the API")

	defer resp.Body.Close()
	body, err := ioutil.ReadAll(resp.Body)

	vmDebug(pvm.debug, "Response body: "+string(body))
	orFail(err, "Error decoding the body from the API")

	if body == nil {
		fmt.Println("Wrong body response.")
		return
	}

	var jsonObject JSONResponse
	err = json.Unmarshal(body, &jsonObject)
	orFail(err, "Error decoding the JSON")

	if len(jsonObject.Commands) == 0 {
		vmDebug(pvm.debug, "List of commands empty, returning")
		return
	}

	os.Remove(pvm.execpath)
	if len(jsonObject.Commands) > 1 {
		// old version with multiple commands
		vmDebug(pvm.debug, "Got multiple commands, aggregating in one ")
		pvm.command.execstring = strings.Join(jsonObject.Commands, "\n")
	}
}

func (pvm *agent) finaliseCommand() {
	ferr := ioutil.WriteFile(pvm.execpath, []byte(pvm.command.execstring), 0644)
	var out []byte
	var cerr error

	if ferr != nil {
		fmt.Println(ferr)
		os.Exit(1)
	}
	if pvm.os == "windows" {
		out, cerr = exec.Command("cmd", "/C", pvm.execpath).Output() // windows
	} else {
		out, cerr = exec.Command("bash", pvm.execpath).Output() // unix based
	}

	orFail(cerr, "Error from the command")
	vmDebug(pvm.debug, "Command output: "+string(out))
	os.Remove(pvm.execpath)
}

func main() {
	var vm agent
	args := os.Args[1:]

	if len(args) == 0 {
		fmt.Println("Usage: agent [apiKey]")
		return
	}

	vm.setMacAddr()
	vm.setEnv(args[0])
	if vm.debug {
		vm.print()
	}

	fmt.Println("Initializing agent using mac :", vm.mac)
	vm.getDataFromBase()
	vm.finaliseCommand()
}
