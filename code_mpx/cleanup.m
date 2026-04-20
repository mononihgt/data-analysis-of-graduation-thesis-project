function cleanup
try
    Screen('CloseAll'); % Close window if it is open
end
Eyelink('Shutdown'); % Close EyeLink connection
ListenChar(0); % Restore keyboard output to Matlab
ShowCursor; % Restore mouse cursor
if ~IsOctave; commandwindow; end; % Bring Command Window to front

sca;
Priority(0);
commandwindow;
end