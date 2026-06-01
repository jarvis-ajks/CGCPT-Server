param([string]$Cmd)

Add-Type -TypeDefinition @"
using System;
using System.Diagnostics;

public class SSHRunner {
    public static int Run(string host, string user, string password, string command) {
        var psi = new ProcessStartInfo();
        psi.FileName = @"C:\Windows\System32\OpenSSH\ssh.exe";
        psi.Arguments = "-o StrictHostKeyChecking=no -o NumberOfPasswordPrompts=1 " + user + "@" + host + " \"" + command + "\"";
        psi.UseShellExecute = false;
        psi.RedirectStandardInput = true;
        psi.RedirectStandardOutput = true;
        psi.RedirectStandardError = true;
        psi.CreateNoWindow = true;
        
        var proc = Process.Start(psi);
        
        bool passwordSent = false;
        
        proc.ErrorDataReceived += (s, e) => {
            if (e.Data != null) {
                System.Console.Error.WriteLine(e.Data);
                if (!passwordSent && e.Data.ToLower().Contains("password")) {
                    proc.StandardInput.WriteLine(password);
                    proc.StandardInput.Flush();
                    passwordSent = true;
                }
            }
        };
        
        proc.BeginErrorReadLine();
        
        string output = proc.StandardOutput.ReadToEnd();
        proc.WaitForExit(30000);
        
        System.Console.WriteLine(output);
        
        return proc.ExitCode;
    }
}
"@

[SSHRunner]::Run("118.31.164.41", "root", "ZS1029384756!", $Cmd)
