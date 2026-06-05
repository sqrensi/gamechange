#include <windows.h>

#include <fstream>
#include <string>

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

void run_python_script(const std::wstring& app_dir, const std::wstring& script_name, const std::wstring& log_name) {
    CreateDirectoryW((app_dir + L"\\output").c_str(), nullptr);

    std::wstring script = app_dir + L"\\" + script_name;
    std::wstring script_log = app_dir + L"\\output\\" + log_name;
    std::wstring command =
        L"cmd.exe /c \"\"python\" \"" + script + L"\" > \"" + script_log + L"\" 2>&1\"";

    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESHOWWINDOW;
    startup.wShowWindow = SW_HIDE;

    PROCESS_INFORMATION process{};
    BOOL ok = CreateProcessW(
        nullptr,
        command.data(),
        nullptr,
        nullptr,
        FALSE,
        CREATE_NO_WINDOW,
        nullptr,
        app_dir.c_str(),
        &startup,
        &process
    );

    if (!ok) {
        write_log(app_dir, "Failed to start " + narrow(script_name) + ". Error: " + std::to_string(GetLastError()));
        return;
    }

    write_log(app_dir, "Started " + narrow(script_name) + ".");
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
}

int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    std::wstring app_dir = app_directory();

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

    write_log(app_dir, "Hotkey runner started. Ctrl+Alt+C captures input/task.txt, Ctrl+Alt+S generates exam/1.txt.");

    MSG message{};
    while (GetMessageW(&message, nullptr, 0, 0) > 0) {
        if (message.message == WM_HOTKEY && message.wParam == SOLVE_HOTKEY_ID) {
            run_python_script(app_dir, L"solve_task.py", L"solve_task.log");
        }

        if (message.message == WM_HOTKEY && message.wParam == CAPTURE_HOTKEY_ID) {
            run_python_script(app_dir, L"capture_task.py", L"capture_task.log");
        }
    }

    UnregisterHotKey(nullptr, SOLVE_HOTKEY_ID);
    UnregisterHotKey(nullptr, CAPTURE_HOTKEY_ID);
    return 0;
}
