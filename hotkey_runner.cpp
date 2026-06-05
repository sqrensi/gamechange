#include <windows.h>

#include <fstream>
#include <string>
#include <vector>

const int SOLVE_HOTKEY_ID = 1;
const int CAPTURE_HOTKEY_ID = 2;

std::wstring app_directory() {
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(nullptr, path, MAX_PATH);

    std::wstring result(path);
    size_t slash = result.find_last_of(L"\\/");
    if (slash == std::wstring::npos) {
        return L".";
    }

    return result.substr(0, slash);
}

std::string narrow(const std::wstring& text) {
    std::string result;
    result.reserve(text.size());
    for (wchar_t ch : text) {
        result.push_back(ch < 128 ? static_cast<char>(ch) : '?');
    }
    return result;
}

void write_log(const std::wstring& app_dir, const std::string& message) {
    CreateDirectoryW((app_dir + L"\\output").c_str(), nullptr);

    std::ofstream log(narrow(app_dir + L"\\output\\hotkey_runner.log"), std::ios::app);
    if (log) {
        log << message << "\n";
    }
}

bool file_exists(const std::wstring& path) {
    DWORD attrs = GetFileAttributesW(path.c_str());
    return attrs != INVALID_FILE_ATTRIBUTES && !(attrs & FILE_ATTRIBUTE_DIRECTORY);
}

std::wstring pythonw_in_folder(const std::wstring& base, const std::wstring& folder) {
    std::wstring candidate = base + folder + L"\\pythonw.exe";
    return file_exists(candidate) ? candidate : L"";
}

std::wstring find_python_launcher() {
    wchar_t buffer[MAX_PATH];
    wchar_t local_app_data[MAX_PATH];
    DWORD local_len = GetEnvironmentVariableW(L"LOCALAPPDATA", local_app_data, MAX_PATH);

    if (local_len > 0 && local_len < MAX_PATH) {
        std::wstring base = std::wstring(local_app_data) + L"\\Programs\\Python\\";

        const wchar_t* preferred_versions[] = {
            L"Python312",
            L"Python313",
            L"Python311",
            L"Python310",
            L"Python39",
        };

        for (const wchar_t* version : preferred_versions) {
            std::wstring candidate = pythonw_in_folder(base, version);
            if (!candidate.empty()) {
                return candidate;
            }
        }

        std::wstring pattern = base + L"Python*";
        WIN32_FIND_DATAW data{};
        HANDLE handle = FindFirstFileW(pattern.c_str(), &data);
        if (handle != INVALID_HANDLE_VALUE) {
            do {
                if (data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                    std::wstring folder = data.cFileName;
                    if (folder == L"Python314") {
                        continue;
                    }

                    std::wstring candidate = pythonw_in_folder(base, folder);
                    if (!candidate.empty()) {
                        FindClose(handle);
                        return candidate;
                    }
                }
            } while (FindNextFileW(handle, &data));
            FindClose(handle);
        }
    }

    if (SearchPathW(nullptr, L"pythonw.exe", nullptr, MAX_PATH, buffer, nullptr)) {
        std::wstring candidate(buffer);
        if (candidate.find(L"Python314") == std::wstring::npos) {
            return candidate;
        }
    }

    if (SearchPathW(nullptr, L"pyw.exe", nullptr, MAX_PATH, buffer, nullptr)) {
        return buffer;
    }

    return L"";
}

DWORD run_python_script(
    const std::wstring& app_dir,
    const std::wstring& python_launcher,
    const std::wstring& script_name,
    const std::wstring& log_name,
    bool wait_for_exit
) {
    CreateDirectoryW((app_dir + L"\\output").c_str(), nullptr);

    std::wstring script = app_dir + L"\\" + script_name;
    std::wstring script_log = app_dir + L"\\output\\" + log_name;
    std::wstring command =
        L"\"" + python_launcher + L"\" \"" + script + L"\" --log \"" + script_log + L"\"";

    std::vector<wchar_t> command_buffer(command.begin(), command.end());
    command_buffer.push_back(L'\0');

    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESHOWWINDOW;
    startup.wShowWindow = SW_HIDE;

    PROCESS_INFORMATION process{};
    BOOL ok = CreateProcessW(
        python_launcher.c_str(),
        command_buffer.data(),
        nullptr,
        nullptr,
        FALSE,
        CREATE_NO_WINDOW | DETACHED_PROCESS,
        nullptr,
        app_dir.c_str(),
        &startup,
        &process
    );

    if (!ok) {
        write_log(app_dir, "Failed to start " + narrow(script_name) + ". Error: " + std::to_string(GetLastError()));
        return 1;
    }

    write_log(app_dir, "Started " + narrow(script_name) + ".");

    if (!wait_for_exit) {
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
        return 0;
    }

    WaitForSingleObject(process.hProcess, INFINITE);

    DWORD exit_code = 1;
    GetExitCodeProcess(process.hProcess, &exit_code);

    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);

    write_log(app_dir, "Finished " + narrow(script_name) + " with code " + std::to_string(exit_code) + ".");
    return exit_code;
}

int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    std::wstring app_dir = app_directory();
    std::wstring python_launcher = find_python_launcher();

    if (python_launcher.empty()) {
        write_log(app_dir, "Python launcher not found. Install Python and ensure pythonw.exe is available.");
        MessageBoxW(nullptr, L"pythonw.exe not found.", L"Hotkey runner", MB_ICONERROR);
        return 1;
    }

    write_log(app_dir, "Using Python launcher: " + narrow(python_launcher));

    if (!RegisterHotKey(nullptr, SOLVE_HOTKEY_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 'S')) {
        write_log(app_dir, "Failed to register Ctrl+Alt+S. Error: " + std::to_string(GetLastError()));
        MessageBoxW(nullptr, L"Could not register Ctrl+Alt+S.", L"Hotkey runner", MB_ICONERROR);
        return 1;
    }

    if (!RegisterHotKey(nullptr, CAPTURE_HOTKEY_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 'C')) {
        write_log(app_dir, "Failed to register Ctrl+Alt+C. Error: " + std::to_string(GetLastError()));
        UnregisterHotKey(nullptr, SOLVE_HOTKEY_ID);
        MessageBoxW(nullptr, L"Could not register Ctrl+Alt+C.", L"Hotkey runner", MB_ICONERROR);
        return 1;
    }

    write_log(app_dir, "Hotkey runner started. Ctrl+Alt+C captures and solves, Ctrl+Alt+S solves exam/1.txt.");

    MSG message{};
    while (GetMessageW(&message, nullptr, 0, 0) > 0) {
        if (message.message == WM_HOTKEY && message.wParam == SOLVE_HOTKEY_ID) {
            run_python_script(app_dir, python_launcher, L"solve_task.py", L"solve_task.log", false);
        }

        if (message.message == WM_HOTKEY && message.wParam == CAPTURE_HOTKEY_ID) {
            DWORD capture_code = run_python_script(
                app_dir,
                python_launcher,
                L"capture_task.py",
                L"capture_task.log",
                true
            );

            if (capture_code == 0) {
                run_python_script(app_dir, python_launcher, L"solve_task.py", L"solve_task.log", false);
            }
        }
    }

    UnregisterHotKey(nullptr, SOLVE_HOTKEY_ID);
    UnregisterHotKey(nullptr, CAPTURE_HOTKEY_ID);
    return 0;
}
