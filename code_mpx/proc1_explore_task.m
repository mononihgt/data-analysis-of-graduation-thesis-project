 try
    clear all;

    %设置  文件路径
    s = pwd;
    addpath(genpath(s));
    path.ori = s;
    path.face = [s '\Stimuli\face'];
    path.EPtask_data = [s '\EPtask_data'];
    path.intro = [s '\Stimuli\intro'];


    subinfo = getsubinfo;
    
%% 
    % 设置参数
    [fix,key,rgb,win,winRect,width,height,sizes,Rect_EPtask,facebar,TRect] = load_EPpara;
    f = load('facelist.mat');
    f = f.facelist;
    facelist = f(str2double(char(subinfo(1))));
    facelist = facelist{1};
    % 加载图片 
    for i = 1:6
        Ftex{i}=load_image(win,path.face,facelist{i},path.ori);
    end
    Ttex{1} = load_image(win,path.intro,'left_match.png',path.ori);
    Ttex{2} = load_image(win,path.intro,'right_match.png',path.ori);
    Ttex{3} = load_image(win,path.intro,'all_match.png',path.ori);
    
%% 探索任务

    test=0;
    Wtex{1}=load_image(win,path.intro,'true.png',path.ori);
    Wtex{2}=load_image(win,path.intro,'false.png',path.ori);

    % 初始化学习数据记录
    allLearnData = [];  % 存储所有学习阶段的坐标点
    returnToLearnCount = 0;  % 记录返回学习阶段的次数
    totalLearnTime = 0;  % 总学习时间
    
    while true
        %学习，按q进入测试
        if test==0
            [test, learnData] = demo_EPtask(win,winRect,rgb,key, Rect_EPtask.square, Ftex, Rect_EPtask.face,Ttex,TRect,facebar,test);
            
            % 如果有学习数据，累加到总数据中
            if ~isempty(learnData)
                % 计算本次学习时长
                if ~isempty(learnData)
                    currentLearnTime = learnData(end).timestamp;
                    totalLearnTime = totalLearnTime + currentLearnTime;
                    
                    % 将当前学习数据添加到总数据中
                    if isempty(allLearnData)
                        allLearnData = learnData;
                    else
                        allLearnData = [allLearnData, learnData];
                    end
                end
            end
        end
        
        %退出
        if test==-1
            sca;
            break;
        end
        
        % 测试，按q返回学习
        if test==1
            [test,result] = demo_EPtest(win,winRect,rgb,Rect_EPtask.square,key,Ftex,Rect_EPtask.testF,facebar,test,subinfo,Wtex);
            
            % 如果从测试返回学习（test==0），增加计数
            if test == 0
                returnToLearnCount = returnToLearnCount + 1;
            end
            
            if ~isempty(result)
                columheader={'SubNo','Name','Gender','Age','Handedness','test_time',...
                    'true_leftBar','true_rightBar','leftBarLength','rightBarLength',...
                    'face','acc','rt'};
                result = orderfields(result,columheader);
                ret = [columheader;(struct2cell(result))'];
                cd(path.EPtask_data);
                currentDate = datestr(now, 'yyyy-mm-dd');
                
                % 检查文件是否存在，如果存在则添加序号
                baseFileName = ['EPtask-',char(subinfo(1)),'-',currentDate];
                fileCounter = 1;
                csvFileName = [baseFileName, '.csv'];
                matFileName = [baseFileName, '.mat'];
                
                while exist(csvFileName, 'file') || exist(matFileName, 'file')
                    csvFileName = [baseFileName, '-', num2str(fileCounter), '.csv'];
                    matFileName = [baseFileName, '-', num2str(fileCounter), '.mat'];
                    fileCounter = fileCounter + 1;
                end
                
                T = cell2table(ret);
                writetable(T, csvFileName, 'WriteVariableNames', false);
                save(matFileName, 'ret');
                cd(path.ori);
            end
        end
    end
    
    % 保存学习数据（如果有）
    if ~isempty(allLearnData)
        % 获取当前日期作为文件名的一部分
        currentDate = datestr(now, 'yyyy-mm-dd');
        
        % 创建学习数据的汇总信息
        learnSummary.SubNo = str2double(char(subinfo(1)));
        learnSummary.Name = char(subinfo(4));
        learnSummary.Date = currentDate;
        learnSummary.TotalLearnTime = totalLearnTime;  % 总学习时间（秒）
        learnSummary.ReturnToLearnCount = returnToLearnCount;  % 返回学习次数
        learnSummary.TotalPoints = length(allLearnData);  % 总记录点数
        learnSummary.CoordinateData = allLearnData;  % 所有坐标点数据
        
        % 保存学习数据
        cd(path.EPtask_data);
        
        % 检查文件是否存在，如果存在则添加序号
        baseFileName = ['EPtask_learning-',char(subinfo(1)),'-',currentDate];
        fileCounter = 1;
        matFileName = [baseFileName, '.mat'];
        
        while exist(matFileName, 'file')
            matFileName = [baseFileName, '-', num2str(fileCounter), '.mat'];
            fileCounter = fileCounter + 1;
        end
        
        save(matFileName, 'learnSummary');
        
        cd(path.ori);
        
        fprintf('学习数据已保存:\n');
        fprintf('- 总学习时间: %.2f 秒 (%.2f 分钟)\n', totalLearnTime, totalLearnTime/60);
        fprintf('- 返回学习次数: %d\n', returnToLearnCount);
        fprintf('- 记录的坐标点数: %d\n', length(allLearnData));
    end

catch    
    ShowCursor;
    Screen('CloseAll');
    psychrethrow(lasterror);
end
