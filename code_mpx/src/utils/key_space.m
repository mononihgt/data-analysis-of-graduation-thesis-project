function key_space(key)
    while KbCheck; end
    while 1  % if press down esp, jump out of exp,if space, goto formal experiemnt
        [key_is_down,~,key_code] = KbCheck;
        if key_is_down
            if key_code(key.esc) % return
                Screen('Closeall');
                return
            end
            if key_code(key.space)
                break;  % terminatewhile loop
            end
        end
    end 
end