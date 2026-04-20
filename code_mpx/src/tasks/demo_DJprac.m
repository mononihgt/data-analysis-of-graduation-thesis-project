function demo_DJprac(win,winRect,key,Ftex,Rect_DJtask,praclist,subinfo,Wtex)
    white = [225 225 225];
    purple = [128, 0, 128];
    green = [0, 255, 0];
    % 获取屏幕中心
    [screenX, screenY] = Screen('WindowSize', win);
    
    % 计算居中位置
    centerX = screenX / 2;
    centerY = screenY / 2;
    
    % 创建居中的矩形
    [textureWidth, textureHeight] = Screen('WindowSize', Wtex{1});
    FRect_centered = [centerX - textureWidth/2, centerY - textureHeight/2, ...
                      centerX + textureWidth/2, centerY + textureHeight/2];

    abnear=mod(str2double(char(subinfo(1))),2);
    exit=0;
    
    for trial = 1:8

        ptb_draw_fixation(win, winRect, green)
        jitter=round(rand * 1 + 1, 1);
        WaitSecs(jitter);

        Screen('Drawtexture',win,Ftex{praclist(trial).F0},[],Rect_DJtask.face);
        Screen('Flip', win);
        WaitSecs(3);

        ptb_draw_fixation(win, winRect, white)
        jitter=round(rand * 1 + 1, 1);
        WaitSecs(jitter);

        if praclist(trial).order==1
            Screen('Drawtexture',win,Ftex{praclist(trial).F1},[],Rect_DJtask.face);
            Screen('Flip', win);
            WaitSecs(3);
        else
            Screen('Drawtexture',win,Ftex{praclist(trial).F2},[],Rect_DJtask.face);
            Screen('Flip', win);
            WaitSecs(3);
        end

        ptb_draw_fixation(win, winRect, purple)
        WaitSecs(1.5);

        Screen('Drawtexture',win,Ftex{praclist(trial).F0},[],Rect_DJtask.face);
        Screen('Flip', win);
        WaitSecs(3);

        ptb_draw_fixation(win, winRect, white)
        jitter=round(rand * 1 + 1, 1);
        WaitSecs(jitter);

        if praclist(trial).order==1
            Screen('Drawtexture',win,Ftex{praclist(trial).F2},[],Rect_DJtask.face);
            Screen('Flip', win);
        else
            Screen('Drawtexture',win,Ftex{praclist(trial).F1},[],Rect_DJtask.face);
            Screen('Flip', win);
        end

        while KbCheck; end
        while 1  % if press down esp, jump out of exp,if space, goto formal experiemnt
            [key_is_down,~,key_code] = KbCheck;
            if key_is_down
                if key_code(key.esc) % return
                    exit=1;
                    break;
                end
                if key_code(key.LeftArrow)
                    answer = 1;
                    feedback(trial,abnear,answer,praclist,win,Wtex,FRect_centered)
                    break;
                elseif key_code(key.RightArrow)
                    answer = 2;
                    feedback(trial,abnear,answer,praclist,win,Wtex,FRect_centered)
                    break;
                end
            end
        end
        
        if exit==1
            break;
        end
    
    end
    

end

function feedback(trial,subnum,answer,praclist,win,Wtex,FRect_centered)
    if praclist(trial).order==1
        if mod(subnum,2)==1
            if answer == praclist(trial).o1_relation_abnear
                Screen('Drawtexture',win,Wtex{1},[],FRect_centered);
                Screen('Flip', win);
                WaitSecs(2);
            else
                Screen('Drawtexture',win,Wtex{2},[],FRect_centered);
                Screen('Flip', win);
                WaitSecs(2);
            end
        else
            if answer == praclist(trial).o1_relation_acnear
                Screen('Drawtexture',win,Wtex{1},[],FRect_centered);
                Screen('Flip', win);
                WaitSecs(2);
            else
                Screen('Drawtexture',win,Wtex{2},[],FRect_centered);
                Screen('Flip', win);
                WaitSecs(2);
            end
        end
    else
        if mod(subnum,2)==1
            if answer == praclist(trial).o2_relation_abnear
                Screen('Drawtexture',win,Wtex{1},[],FRect_centered);
                Screen('Flip', win);
                WaitSecs(2);
            else
                Screen('Drawtexture',win,Wtex{2},[],FRect_centered);
                Screen('Flip', win);
                WaitSecs(2);
            end
        else
            if answer == praclist(trial).o2_relation_acnear
                Screen('Drawtexture',win,Wtex{1},[],FRect_centered);
                Screen('Flip', win);
                WaitSecs(2);
            else
                Screen('Drawtexture',win,Wtex{2},[],FRect_centered);
                Screen('Flip', win);
                WaitSecs(2);
            end
        end
    end
end
