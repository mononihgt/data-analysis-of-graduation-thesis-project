function [fix,key,rgb,win,winRect,width,height,sizes,Rect_SPtask,facebar] = load_SPpara()
%% 准备实验参数
    %  颜色
    rgb.black = [0,0,0];
    rgb.white = [255,255,255];
    
    fix = '+';
        
    % -------------------------------- for keyboard and mouse
    %     define key
    KbName('UnifyKeyNames');
    key.esc = KbName('ESCAPE');  % return key code
    key.space = KbName('SPACE'); 
    key.LeftArrow= KbName('LeftArrow');
    key.RightArrow = KbName('RightArrow');
    key.UpArrow = KbName('UpArrow');
    key.DownArrow = KbName('DownArrow');
    
    %  窗口
    %  测试 2 ，正式实验1
    AssertOpenGL;
    Screen('Preference', 'SkipSyncTests', 1);
    screenNumber = max(Screen('Screens'));
    [win, winRect] = Screen('OpenWindow', screenNumber,rgb.black);

    % rect=[0 0 1000 800];
    % [win, winRect] = Screen('OpenWindow', screenNumber,rgb.black,rect);

    width=winRect(3);
    height=winRect(4);

    topPriorityLevel = MaxPriority(win);
    [center_x,center_y] = RectCenter(winRect);
    
    
    %% 设置图片出现位置
    sizes.face=[0 0 200 201];
    sizes.square=[0 0 400 400];

    for r = 0:1
        for c = 1:3
            if r==0
                Rect_SPtask.face(r*3+c,:) = [center_x-400+300*(c-1) center_y-251 center_x-200+300*(c-1) center_y-50];
            elseif r==1
                Rect_SPtask.face(r*3+c,:) = [center_x-400+300*(c-1) center_y+50 center_x-200+300*(c-1) center_y+251];
            end
        end
    end
    Rect_SPtask.intro = [center_x-309/2 center_y+300 center_x+309/2 center_y+420];

    %% 化身坐标
        facevalue = [2.416, 4.788;
                 2.789, 7.765;
                 6.426, 8.527;
                 8.817, 6.716;
                 4.894, 2.020;
                 7.659, 3.185];
    facebar = round((facevalue/10) * 400);
end