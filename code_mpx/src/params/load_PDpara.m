function [fix,key,rgb,win,winRect,width,height,sizes,Rect_PDtask,facebar,triallist] = load_PDpara()

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
    cfg = experiment_config(screenNumber, winRect);

    % rect=[0 0 1000 800];
    % [win, winRect] = Screen('OpenWindow', screenNumber,rgb.black,rect);

    width=winRect(3);
    height=winRect(4);

    topPriorityLevel = MaxPriority(win);
    [center_x,center_y] = RectCenter(winRect);
    
    
    %% 设置图片出现位置
    sizes.face=[0 0 200 201];
    Rect_PDtask.face=[center_x+(1/6)*width-300 center_y-100 center_x+(1/6)*width-100 center_y+101;
                      center_x+(1/6)*width+100 center_y-100 center_x+(1/6)*width+300 center_y+101];
    Rect_PDtask.intro=[center_x+(1/6)*width-500 center_y+200 center_x+(1/6)*width+500 center_y+500];

    squareHalf = cfg.squareSidePx / 2;
    sizes.square=[0 0 cfg.squareSidePx cfg.squareSidePx];
    Rect_PDtask.square=[center_x-(1/6)*width-squareHalf center_y-squareHalf center_x-(1/6)*width+squareHalf center_y+squareHalf];

    %% 化身坐标
    facevalue = [0.60, 6.20;
                 4.60, 6.35;
                 6.69, 5.85;
                 8.55, 9.39;
                 5.21, 4.30;
                 7.34, 0.91];
    facebar = (facevalue/10) * cfg.squareSidePx;

    % 试次表
    Flist = PDtask_trial();
    for i = 1:length(Flist)
        triallist(i,1).F1=Flist(i,1);
        triallist(i,1).F1V=village(Flist(i,1));
        triallist(i,1).F1X=facebar(Flist(i,1),1);
        triallist(i,1).F1Y=facebar(Flist(i,1),2);
        triallist(i,1).F2=Flist(i,2);
        triallist(i,1).F2V=village(Flist(i,2));
        triallist(i,1).F2X=facebar(Flist(i,2),1);
        triallist(i,1).F2Y=facebar(Flist(i,2),2);
        triallist(i,1).D=norm(facebar(Flist(i,1),:)-facebar(Flist(i,2),:));
        triallist(i,1).MidX=(facebar(Flist(i,1),1)+facebar(Flist(i,2),1))/2;
        triallist(i,1).MidY=(facebar(Flist(i,1),2)+facebar(Flist(i,2),2))/2;
        triallist(i,1).Mtask=Flist(i,3);
    end

end

function v=village(face)
    if face==1||face==2
        v=1;
    elseif face==3||face==4
        v=2;
    elseif face==5||face==6
        v=3;
    end
end
