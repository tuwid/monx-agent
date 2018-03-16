package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
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
// - Add selfupdate

type JSONResponse struct {
	Commands []string `json:"commands"`
}

type agent struct {
	mac       string
	apikey    string
	version   string
	apiuri    string
	agentpath string
	execpath  string
	separator string
	debug     bool
	os        string
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

func getUpdateFromURL(filepath string, url string) error {
	out, err := os.Create(filepath)
	orFail(err, "Error creating a temp path for agent update")
	defer out.Close()
	resp, err := http.Get(url)
	orFail(err, "Error while GETing agent update from GITHUB")
	defer resp.Body.Close()
	_, err = io.Copy(out, resp.Body)
	orFail(err, "Error while writing agent update to file")
	return nil
}

func (pvm *agent) print() {
	fmt.Println("Agent VER: ", pvm.version)
	fmt.Println("Agent MAC: ", pvm.mac)
	fmt.Println("Agent KEY: ", pvm.apikey)
	fmt.Println("Agent URI: ", pvm.apiuri)
	fmt.Println("Agent OS: ", pvm.os)
	fmt.Println("Agent TMP_PATH: ", pvm.execpath)
	fmt.Println("Agent RUN_PATH: ", pvm.agentpath)
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

func (pvm *agent) selfUpdate() {
	vmDebug(pvm.debug, "Starting slef update subrutine")
	dir, err := filepath.Abs(filepath.Dir(pvm.agentpath))
	orFail(err, "Error while reading path")
	vmDebug(pvm.debug, "Getting last agent build")
	fileUrl := "https://github.com/tuwid/monx-agent/raw/master/builds/agent-latest"
	updatedFile := dir + pvm.separator + "agent_update"
	error := getUpdateFromURL(updatedFile, fileUrl)
	orFail(error, "Error while getUpdateFromURL")
	os.Rename(pvm.agentpath, pvm.agentpath+".bck")
	os.Rename(updatedFile, pvm.agentpath)
	if pvm.os != "windows" {
		os.Chmod(pvm.agentpath, 0755)
	}
}

func (pvm *agent) setEnv(key []string) {
	pvm.os = runtime.GOOS
	pvm.version = "1.1.1"
	if os.Getenv("AGENT_DEBUG") == "1" {
		fmt.Println("Turning ON debug logs")
		pvm.debug = true
	}

	pvm.agentpath = key[0]
	pvm.apikey = key[1]
	pvm.apiuri = "https://api.monx.me/api/hub/agent/command?apikey=" + pvm.apikey + "&mac=" + pvm.mac
	if pvm.os == "windows" {
		pvm.separator = "\\"
		// pvm.execpath = filepath.Join(os.Getenv("TEMP"), "_monxagent.bat")
		pvm.execpath = filepath.Join("C:\\_monxagent.bat")
	} else {
		pvm.separator = "/"
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
		vmDebug(pvm.debug, "Got multiple commands, will aggregate")
	}
	pvm.command.execstring = strings.Join(jsonObject.Commands, "\n")
}

func (pvm *agent) finaliseCommand() {
	fmt.Println(pvm.command.execstring)
	if pvm.command.execstring == "_autoUpdate" {
		vmDebug(pvm.debug, "Starting slef update")
		pvm.selfUpdate()
	} else {
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
}

func main() {
	var vm agent
	args := os.Args

	if len(args[1:]) == 0 {
		fmt.Println("Usage: agent [apiKey]")
		return
	}

	vm.setMacAddr()
	vm.setEnv(args)
	if vm.debug {
		vm.print()
	}

	fmt.Println("Initializing agent using mac :", vm.mac)
	vm.getDataFromBase()
	vm.finaliseCommand()
}
