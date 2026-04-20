function result = demo_DJtask(win,winRect,key,Ftex,Rect_DJtask,triallist,subinfo)

    white = [225 225 225];
    purple = [128, 0, 128];
    green = [0, 255, 0];

    subnum = str2double(char(subinfo(1)));
    result = [];
    
    for trial = 1:length(triallist)

        ptb_draw_fixation(win, winRect, green)
        jitter=round(rand * 1 + 1, 1);
        WaitSecs(jitter);

        Screen('Drawtexture',win,Ftex{triallist(trial).F0},[],Rect_DJtask.face);
        Screen('Flip', win);
        WaitSecs(3);

        ptb_draw_fixation(win, winRect, white)
        jitter=round(rand * 1 + 2, 1);
        WaitSecs(jitter);

        if triallist(trial).order==1
            Screen('Drawtexture',win,Ftex{triallist(trial).F1},[],Rect_DJtask.face);
            Screen('Flip', win);
            WaitSecs(3);
        else
            Screen('Drawtexture',win,Ftex{triallist(trial).F2},[],Rect_DJtask.face);
            Screen('Flip', win);
            WaitSecs(3);
        end

        ptb_draw_fixation(win, winRect, purple)
        WaitSecs(1.5);

        Screen('Drawtexture',win,Ftex{triallist(trial).F0},[],Rect_DJtask.face);
        Screen('Flip', win);
        WaitSecs(3);

        ptb_draw_fixation(win, winRect, white)
        jitter=round(rand * 1 + 1, 1);
        WaitSecs(jitter);

        if triallist(trial).order==1
            Screen('Drawtexture',win,Ftex{triallist(trial).F2},[],Rect_DJtask.face);
            Tsec=Screen('Flip', win);
        else
            Screen('Drawtexture',win,Ftex{triallist(trial).F1},[],Rect_DJtask.face);
            Tsec=Screen('Flip', win);
        end

        while KbCheck; end
        while 1  % if press down esp, jump out of exp,if space, goto formal experiemnt
            [key_is_down,~,key_code] = KbCheck;
            if key_is_down
                if key_code(key.esc) % return
                    Screen('Closeall');
                    return
                end
                if key_code(key.LeftArrow)
                    answer = 1;
                    rt=GetSecs()-Tsec;
                    [acc, correct_ans]=check(trial,subnum,answer,triallist);
                    break;
                elseif key_code(key.RightArrow)
                    answer = 2;
                    rt=GetSecs()-Tsec;
                    [acc, correct_ans]=check(trial,subnum,answer,triallist);
                    break;
                end
            end
        end

        result = record(result,trial,triallist,subinfo,correct_ans,answer,acc,rt);

    
    end
    

end

function [acc, correct_ans]=check(trial,subnum,answer,triallist)
    if triallist(trial).order==1
        if mod(subnum,2)==1
            correct_ans = triallist(trial).o1_relation_abnear;
            if answer == triallist(trial).o1_relation_abnear
                acc=1;
            else
                acc=0;
            end
        else
            correct_ans = triallist(trial).o1_relation_acnear;
            if answer == triallist(trial).o1_relation_acnear
                acc=1;
            else
                acc=0;
            end
        end
    else
        if mod(subnum,2)==1
            correct_ans = triallist(trial).o2_relation_abnear;
            if answer == triallist(trial).o2_relation_abnear
                acc=1;
            else
                acc=0;
            end
        else
            correct_ans = triallist(trial).o2_relation_acnear;
            if answer == triallist(trial).o2_relation_acnear
                acc=1;
            else
                acc=0;
            end
        end
    end
end

function result=record(result, trial,triallist,subinfo,correct_ans,answer,acc,rt)
    if str2double(char(subinfo(2))) == 1
        Gender = 'Male';
    else
        Gender = 'Female';
    end
    %-------------------------------------------
    if str2double(char(subinfo(5))) == 1
        Handedness = 'Right';
    else
        Handedness = 'Left';
    end
    result(trial,1).SubNo = str2double(char(subinfo(1)));
    result(trial,1).Name = char(subinfo(4));
    result(trial,1).Gender = Gender;
    result(trial,1).Age = str2double(char(subinfo(3)));
    result(trial,1).Handedness = Handedness;
    result(trial,1).F0 = triallist(trial).F0;
    result(trial,1).F1 = triallist(trial).F1;
    result(trial,1).F2 = triallist(trial).F2;
    result(trial,1).F0V = triallist(trial).F0V;
    result(trial,1).F1V = triallist(trial).F1V;
    result(trial,1).F2V = triallist(trial).F2V;
    result(trial,1).type = triallist(trial).type;
    result(trial,1).order = triallist(trial).order;  
    result(trial,1).correct_ans = correct_ans;
    result(trial,1).answer = answer;
    result(trial,1).acc = acc;
    result(trial,1).rt = rt;

end
