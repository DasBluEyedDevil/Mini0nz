import subprocess
import json
import sys
import os

def run_loop(task):
    # Paths to agents
    # Assuming this script is run from project root, and scripts are in .skills/
    # Use forward slashes for bash compatibility on Windows
    gemini_agent = ".skills/gemini.agent.wrapper.sh"
    codex_agent = ".skills/codex.agent.wrapper.sh"
    copilot_agent = ".skills/copilot.agent.wrapper.sh"

    # 1. Ask Gemini to Analyze
    print("👀 Asking Gemini to analyze...")
    try:
        # We don't capture output here exclusively because the wrapper script manages the memory file
        # But we can capture it to pass to the next agent if we want, or read from memory.
        # The prompt implies passing the output of Gemini to the next agent.
        # gemini.agent.wrapper.sh now writes to .skills/memory.json, but it also echos to stdout.
        # Let's verify gemini agent is executable (bash script on windows might need ensuring via git bash or similar if run via subprocess)
        # On Windows, running .sh files directly might need 'bash' command prefix if not associated.
        # Assuming the user has a bash environment (since they provided bash scripts).
        
        # We'll use 'bash' to run the scripts.
        subprocess.check_call(["bash", gemini_agent, task])
        
        # Read from shared memory
        memory_file = os.path.join(".skills", "memory.json")
        with open(memory_file, 'r') as f:
            memory = json.load(f)
            analysis = memory.get("last_analysis", "")
            
    except subprocess.CalledProcessError as e:
        print(f"Error running Gemini: {e}")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    # 2. Decide who builds (Simple logic)
    if "UI" in task or "Screen" in task or "design" in task.lower():
        agent = codex_agent
        agent_name = "Codex"
    else:
        agent = copilot_agent
        agent_name = "Copilot"
        
    # 3. Execute Builder
    print(f"🛠️ Delegating to {agent_name}...")
    try:
        subprocess.run(["bash", agent, f"Task: {task}", f"Context: {analysis}"])
    except Exception as e:
         print(f"Error running {agent_name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python orchestrate.py \"<Task Description>\"")
        sys.exit(1)
        
    task_description = sys.argv[1]
    run_loop(task_description)
