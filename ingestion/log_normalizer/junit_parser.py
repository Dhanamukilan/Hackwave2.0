import xml.etree.ElementTree as ET
import json
from typing import List, Dict, Any, Optional
from ingestion.log_normalizer.normalizer import extract_error_signature

def parse_junit_xml(xml_content: str) -> List[Dict[str, Any]]:
    """
    Parses JUnit XML string and returns list of test case records with parsed failures.
    """
    results = []
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return results

    # Handle <testsuite> wrappers as well as direct <testcase> children under <testsuites>
    testsuites = []
    if root.tag == "testsuite":
        testsuites = [root]
    else:
        testsuites = root.findall(".//testsuite")

    # If testsuite elements exist, iterate through them
    if testsuites:
        suites_to_process = testsuites
    else:
        # Node.js and some other runners put <testcase> directly under <testsuites>
        suites_to_process = [root]

    for suite in suites_to_process:
        suite_name = suite.attrib.get("name", "default_suite")
        
        for case in suite.findall("testcase"):
            test_name = case.attrib.get("name", "unknown_test")
            classname = case.attrib.get("classname", suite_name)
            file_path = case.attrib.get("file", classname.replace(".", "/") + ".py")
            line = int(case.attrib.get("line", 0)) if case.attrib.get("line") else None
            time_taken = float(case.attrib.get("time", 0.0))

            failure_el = case.find("failure")
            error_el = case.find("error")
            skipped_el = case.find("skipped")

            status = "PASSED"
            error_info = None

            if failure_el is not None or error_el is not None:
                status = "FAILED"
                target = failure_el if failure_el is not None else error_el
                raw_msg = target.attrib.get("message", "")
                stack = (target.text or "").strip()
                combined_log = f"{raw_msg}\n{stack}" if stack else raw_msg

                sig = extract_error_signature(combined_log)
                attr_type = target.attrib.get("type")
                if attr_type and attr_type not in ["testCodeFailure", "testTimeoutFailure", "failure", "error"]:
                    err_type = attr_type
                elif sig["error_type"] != "UnknownError":
                    err_type = sig["error_type"]
                else:
                    err_type = attr_type or sig["error_type"]

                error_info = {
                    "error_type": err_type,
                    "raw_message": raw_msg or sig["raw_message"],
                    "normalized_message": sig["normalized_message"],
                    "stack_trace": stack,
                    "normalized_stack_trace": sig["normalized_text"],
                    "fingerprint_hash": sig["fingerprint_hash"],
                    "location": sig["location"] or f"{file_path}:{line}" if line else file_path
                }
            elif skipped_el is not None:
                status = "SKIPPED"

            results.append({
                "name": test_name,
                "suite_name": suite_name,
                "file_path": file_path,
                "line_number": line,
                "duration_seconds": time_taken,
                "status": status,
                "error_info": error_info
            })

    return results

def parse_test_json(json_content: str) -> List[Dict[str, Any]]:
    """
    Parses JSON test execution report (e.g. pytest-json-report or Jest JSON output).
    """
    results = []
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        return results

    # Support pytest-json-report format
    tests = data.get("tests", [])
    for t in tests:
        nodeid = t.get("nodeid", "")
        parts = nodeid.split("::")
        file_path = parts[0] if parts else "test.py"
        test_name = parts[-1] if len(parts) > 1 else nodeid
        outcome = t.get("outcome", "passed").upper()

        error_info = None
        if outcome in ["FAILED", "ERROR"]:
            call_info = t.get("call", {})
            crash = call_info.get("crash", {})
            raw_msg = crash.get("message", "")
            traceback = call_info.get("traceback", "")
            combined = f"{raw_msg}\n{traceback}"
            sig = extract_error_signature(combined)
            error_info = {
                "error_type": sig["error_type"],
                "raw_message": raw_msg,
                "normalized_message": sig["normalized_message"],
                "stack_trace": traceback,
                "normalized_stack_trace": sig["normalized_text"],
                "fingerprint_hash": sig["fingerprint_hash"],
                "location": sig["location"] or file_path
            }

        results.append({
            "name": test_name,
            "suite_name": file_path,
            "file_path": file_path,
            "line_number": crash.get("lineno") if error_info and "crash" in locals() else None,
            "duration_seconds": float(t.get("duration", 0.0)),
            "status": "FAILED" if outcome in ["FAILED", "ERROR"] else ("SKIPPED" if outcome == "SKIPPED" else "PASSED"),
            "error_info": error_info
        })

    return results
